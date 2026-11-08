"""读取公开的官方 CDS 数据集目录，不需要账号凭据。"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlsplit

import requests


CATALOGUE_URL = 'https://cds.climate.copernicus.eu/api/catalogue/v1/datasets'


def fetch_catalogue() -> list[dict[str, str]]:
    url = f'{CATALOGUE_URL}?limit=100'
    seen: set[str] = set()
    items: dict[str, dict[str, str]] = {}
    deadline = time.monotonic() + 90
    with requests.Session() as session:
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
