"""读取公开的官方 CDS 数据集目录，不需要账号凭据。"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlsplit

import requests

from ecmwf_downloader.config import NetworkProxySettings
from ecmwf_downloader.infrastructure.network import request_session


CATALOGUE_URL = 'https://cds.climate.copernicus.eu/api/catalogue/v1/datasets'


def fetch_catalogue(network: NetworkProxySettings | None = None) -> list[dict[str, str]]:
    url = f'{CATALOGUE_URL}?limit=100'
    seen: set[str] = set()
    items: dict[str, dict[str, str]] = {}
    deadline = time.monotonic() + 90
    with request_session(network) as session:
        while url:
            # 仅跟随官方目录分页链接，循环或不完整结果不作为完整目录发布。
            target = urlsplit(url)
            if (target.scheme, target.netloc, target.path.rstrip('/')) != (
                'https', 'cds.climate.copernicus.eu', urlsplit(CATALOGUE_URL).path
            ) or url in seen or len(seen) >= 100 or time.monotonic() >= deadline:
                raise ValueError('官方目录分页无效或超时')
            seen.add(url)
            response = session.get(url, timeout=(10, 25))
            response.raise_for_status()
            page = response.json()
            collections = page.get('collections')
            if not isinstance(collections, list):
                raise ValueError('官方目录格式无效')
            for collection in collections:
                dataset_id = collection.get('id')
                title = collection.get('title')
                if not isinstance(dataset_id, str) or not dataset_id or not isinstance(title, str) or not title:
                    raise ValueError('官方目录条目不完整')
                items[dataset_id] = {'id': dataset_id, 'title': title, 'source': 'CDS'}
            next_links = [link['href'] for link in page.get('links', []) if link.get('rel') == 'next' and link.get('href')]
            url = urljoin(url, next_links[0]) if next_links else ''
    if not items:
        raise ValueError('官方目录为空')
    return sorted(items.values(), key=lambda item: (item['title'].casefold(), item['id']))


def check_network(network: NetworkProxySettings) -> tuple[bool, str]:
    try:
        with request_session(network) as session:
            response = session.get(f'{CATALOGUE_URL}?limit=1', timeout=(5, 10), allow_redirects=False)
            response.raise_for_status()
            document = response.json()
            if isinstance(document, dict) and document.get('collections'):
                return True, '已连通 CDS 官方目录。'
    except requests.exceptions.SSLError:
        return False, 'TLS 证书校验失败，请检查代理或证书配置。'
    except requests.Timeout:
        return False, '访问 CDS 超时，请检查网络与代理设置。'
    except requests.ConnectionError:
        return False, '无法连接 CDS，请检查网络与代理设置。'
    except requests.HTTPError as error:
        return False, f'CDS 返回 HTTP {error.response.status_code}。'
    except requests.RequestException:
        pass
    return False, '未收到有效的 CDS 官方目录响应。'
