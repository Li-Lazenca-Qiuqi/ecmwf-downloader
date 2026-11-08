"""公开 NCAR 镜像目录与文件链接，不传输数据文件。"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree as ET

import requests

from ecmwf_downloader.infrastructure.cds import ProviderError

NCAR_ID = 'mirror-ncar-era5'
GDEX_ID = 'mirror-ncar-gdex-era5'
ARCO_ID = 'mirror-arco-era5'
FILE_MIRROR_IDS = frozenset({NCAR_ID, GDEX_ID})
MIRROR_IDS = FILE_MIRROR_IDS
NCAR_URL = 'https://nsf-ncar-era5.s3.us-west-2.amazonaws.com'
GDEX_URL = 'https://data.gdex.ucar.edu/d633000'
GDEX_CATALOG_URL = 'https://tds.gdex.ucar.edu/thredds/catalog/files/g/d633000'
DEFAULT_PREFIX = 'e5.oper.an.sfc/202401/'


def ncar_key(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'e5\.[A-Za-z0-9_.-]+/\d{6}/[A-Za-z0-9_.-]+\.nc', value):
        raise ValueError('NCAR 文件键格式无效，请从已发布文件列表选择')
    return value


def field(name: str, label: str, kind: str, *, values: list | None = None, required: bool = False, default: Any = None, description: str = '') -> dict:
    return {'name': name, 'label': label, 'field_type': kind, 'request_field': True,
            'required': required, 'default': default, 'description': description,
            'options': [{'value': value, 'label': str(value)} for value in values or []]}


def ncar_schema(prefix: str = DEFAULT_PREFIX) -> dict:
    if not re.fullmatch(r'e5\.[A-Za-z0-9_.-]+/\d{6}/', prefix):
        raise ValueError('NCAR 目录需要形如 e5.oper.an.sfc/202401/，仅列出指定产品的一个月')
    options = []
    token = None
    seen = set()
    with requests.Session() as session:
        while True:
            params = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
            if token: params['continuation-token'] = token
            response = session.get(NCAR_URL, params=params, timeout=(10, 30))
            response.raise_for_status()
            root = ET.fromstring(response.content)
            ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
            for item in root.findall('s:Contents', ns):
                key = item.findtext('s:Key', '', ns)
                size = int(item.findtext('s:Size', '0', ns))
                if key.endswith('.nc') and key.startswith(prefix) and key not in seen:
                    ncar_key(key)
                    seen.add(key)
                    options.append({'value': key, 'label': f'{Path(key).name} ({size / 1024**2:.1f} MiB)', 'size_bytes': size})
            if root.findtext('s:IsTruncated', 'false', ns) != 'true': break
            following = root.findtext('s:NextContinuationToken', '', ns)
            if not following or following == token or len(options) > 10000:
                raise ValueError('NCAR 目录分页异常，请缩小目录范围')
            token = following
    item = field('object_key', '已发布 NetCDF 文件', 'multiple', required=True,
                 description='每个文件返回一个原文件链接，不裁剪区域或转换格式；文件可能包含全球整月数据。')
    item['options'] = options
    item['presentation'] = 'files'
    if not options:
        raise ValueError('该目录没有已发布的 NetCDF 文件，请更换产品或年月')
    return {'collection_id': NCAR_ID, 'title': 'NCAR AWS ERA5 · NetCDF 文件', 'fields': [item],
            'description': '匿名访问，无需 CDS 账号；返回已发布文件链接。', 'prefix': prefix, 'source_url': NCAR_URL}


def gdex_schema(prefix: str = DEFAULT_PREFIX) -> dict:
    if not re.fullmatch(r'e5\.[A-Za-z0-9_.-]+/\d{6}/', prefix):
        raise ValueError('NCAR 目录需要形如 e5.oper.an.sfc/202401/')
    catalog_url = f'{GDEX_CATALOG_URL}/{prefix}catalog.xml'
    response = requests.get(catalog_url, timeout=(10, 30))
    response.raise_for_status()
    root = ET.fromstring(response.content)
    ns = {'t': 'http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0'}
    options = []
    seen = set()
    for item in root.findall('.//t:dataset', ns):
        path = item.get('urlPath', '')
        for base in ('files/d633000/', 'files/g/d633000/'):
            if path.startswith(base):
                key = path[len(base):]
                break
        else:
            continue
        if not key.startswith(prefix) or not key.endswith('.nc') or key in seen:
            continue
        ncar_key(key)
        seen.add(key)
        size = item.find('t:dataSize', ns)
        # 使用目录原始单位，不将四舍五入的大小误报为精确字节数。
        suffix = f' ({size.text} {size.get("units", "")})' if size is not None and size.text else ''
        options.append({'value': key, 'label': f'{Path(key).name}{suffix}'})
    if not options:
        raise ValueError('GDEX 目录没有可下载的 NetCDF 文件，请更换产品或年月')
    files = field('object_key', '已发布 NetCDF 文件', 'multiple', required=True,
                  description='每个文件一个链接，不裁剪区域或按日期拆分。')
    files['options'] = sorted(options, key=lambda item: item['value'])
    files['presentation'] = 'files'
    return {'collection_id': GDEX_ID, 'title': 'NCAR GDEX ERA5 · NetCDF 文件', 'fields': [files],
            'description': 'NCAR 自有站点，目录来自 THREDDS，返回 GDEX HTTPS 文件链接。',
            'prefix': prefix, 'source_url': GDEX_URL, 'catalog_url': catalog_url}



class MirrorProvider:
    def results(self, dataset_id, payload):
        key = ncar_key(payload['object_key'])
        base = GDEX_URL if dataset_id == GDEX_ID else NCAR_URL
        url = base + '/' + quote(key, safe='/')
        try:
            # HEAD 仅获取响应头，不读取科学数据文件体。
            with requests.head(url, allow_redirects=True, timeout=(10, 20)) as response:
                response.raise_for_status()
                if response.headers.get('Content-Type', '').startswith('text/html'):
                    raise ProviderError('镜像返回网页，当前文件链接不可用')
                size = response.headers.get('Content-Length')
                return [{"url": response.url, "filename": Path(key).name,
                         "size": int(size) if size is not None else None,
                         "content_type": response.headers.get('Content-Type')}]
        except ProviderError:
            raise
        except Exception:
            raise ProviderError('无法核实镜像文件链接，请稍后重试；未读取文件体。') from None
