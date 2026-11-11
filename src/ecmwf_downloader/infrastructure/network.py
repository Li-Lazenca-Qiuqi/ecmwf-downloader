"""为后端出站请求选择直连、系统代理或手动代理。"""

from __future__ import annotations

import base64
from functools import lru_cache
from fnmatch import fnmatchcase
import os
import shutil
import subprocess
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.request import getproxies, proxy_bypass

import requests

from ecmwf_downloader.config import NetworkProxySettings, network_proxy_url


def _wsl_gateway() -> str | None:
    result = subprocess.run(['ip', '-4', 'route', 'show', 'default'], capture_output=True, text=True, timeout=2)
    route = result.stdout.split()
    return route[2] if route[:2] == ['default', 'via'] else None


def _host_proxy_address(address: str) -> str:
    address = network_proxy_url(address if '://' in address else 'http://' + address)
    proxy = urlsplit(address)
    if proxy.hostname not in {'localhost', '127.0.0.1', '::1'}:
        return address
    wslinfo = shutil.which('wslinfo')
    if wslinfo and subprocess.run([wslinfo, '--networking-mode'], capture_output=True, text=True,
                                  timeout=2).stdout.strip() == 'mirrored':
        return address
    gateway = _wsl_gateway()
    if not gateway:
        return address
    host = f'{gateway}:{proxy.port}' if proxy.port is not None else gateway
    return urlunsplit((proxy.scheme, host, '', '', ''))


@lru_cache(maxsize=2)
def _windows_internet_settings(_time_slot: int) -> dict[str, str]:
    registry = shutil.which('reg.exe') or '/mnt/c/Windows/System32/reg.exe'
    try:
        result = subprocess.run(
            [registry, 'query', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings'],
            capture_output=True, encoding='utf-8', errors='replace', timeout=5, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    values = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0] in {'ProxyEnable', 'ProxyServer', 'ProxyOverride', 'AutoConfigURL'}:
            values[fields[0]] = fields[2]
    return values


def _windows_pac_address(target: str) -> str:
    powershell = shutil.which('powershell.exe') or '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
    target_data = base64.b64encode(target.encode()).decode()
    command = (
        f"$uri = [uri][Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{target_data}'));"
        "$resolved = [System.Net.WebRequest]::GetSystemWebProxy().GetProxy($uri);"
        "if ($resolved -ne $uri) { $resolved.AbsoluteUri }"
    )
    encoded = base64.b64encode(command.encode('utf-16-le')).decode()
    return subprocess.run(
        [powershell, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
        capture_output=True, text=True, timeout=8, check=True,
    ).stdout.strip()


@lru_cache(maxsize=32)
def _windows_system_proxy(target: str, time_slot: int) -> str | None:
    settings = _windows_internet_settings(time_slot)
    try:
        if settings.get('AutoConfigURL'):
            address = _windows_pac_address(target)
        elif settings.get('ProxyEnable') == '0x1':
            host = (urlsplit(target).hostname or '').casefold()
            exclusions = settings.get('ProxyOverride', '').casefold().split(';')
            if any((item == '<local>' and '.' not in host) or fnmatchcase(host, item) for item in exclusions):
                return None
            address = settings.get('ProxyServer', '')
            if '=' in address:
                protocols = dict(item.split('=', 1) for item in address.split(';') if '=' in item)
                address = protocols.get(urlsplit(target).scheme, '')
        else:
            return None
        return _host_proxy_address(address) if address else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _uses_windows_system_proxy() -> bool:
    return bool(os.environ.get('WSL_DISTRO_NAME') and not getproxies().keys() & {'http', 'https', 'all'})


def explicit_proxy(settings: NetworkProxySettings, url: str) -> str | None:
    if settings.mode == 'manual':
        return settings.url
    if settings.mode != 'system' or not _uses_windows_system_proxy():
        return None
    target = urlsplit(url)
    if proxy_bypass(target.netloc):
        return None
    origin = urlunsplit((target.scheme, target.netloc, '/', '', ''))
    return _windows_system_proxy(origin, int(time.monotonic() // 10))


class _NetworkSession(requests.Session):
    def __init__(self, network: NetworkProxySettings):
        super().__init__()
        self._network = network

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        settings = super().merge_environment_settings(url, proxies, stream, verify, cert)
        address = explicit_proxy(self._network, url)
        if address:
            settings['proxies'] = {'http': address, 'https': address}
        elif self._network.mode == 'direct':
            settings['proxies'] = {}
        return settings

    def rebuild_proxies(self, prepared_request, proxies):
        # 重定向到新的主机时重新应用代理模式，直连模式也继续绕过环境代理。
        address = explicit_proxy(self._network, prepared_request.url)
        if address or self._network.mode == 'direct' or _uses_windows_system_proxy():
            prepared_request.headers.pop('Proxy-Authorization', None)
            return {'http': address, 'https': address} if address else {}
        return super().rebuild_proxies(prepared_request, proxies)


def request_session(network: NetworkProxySettings | None = None) -> requests.Session:
    return _NetworkSession(network) if network is not None else requests.Session()
