"""查询完整在线字段并明确缓存、失败和约束来源。"""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import math
from datetime import datetime, timezone
import threading
import time
from typing import Any, Optional
import requests
from ecmwf_downloader.domain.schema import finish_schema

from ecmwf_downloader.infrastructure.catalogue import fetch_catalogue
from ecmwf_downloader.infrastructure.datastores import DatastoresProvider
from ecmwf_downloader.infrastructure.mirrors import ARCO_ID, NCAR_ID, GDEX_ID, FILE_MIRROR_IDS, MIRROR_IDS, DEFAULT_PREFIX, ncar_schema, gdex_schema


class DatasetService:
    def __init__(self):
        self._cache: dict[tuple, tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self._catalogue_lock = threading.Lock()
        self._catalogue_cache: tuple[float, dict] | None = None

    def list(self, query: str = '', *, refresh: bool = False, source: str = 'cds') -> dict[str, Any]:
        if source == 'arco': raise ValueError('ARCO 本地导出已移除')
        if source in {'ncar', 'gdex'}:
            item = {'ncar': {'id': NCAR_ID, 'title': 'NCAR AWS ERA5 · NetCDF 文件', 'source': 'NCAR AWS'},
                    'gdex': {'id': GDEX_ID, 'title': 'NCAR GDEX ERA5 · NetCDF 文件', 'source': 'NCAR GDEX'}}[source]
            items = [item] if all(word in f"{item['id']} {item['title']}".casefold() for word in query.casefold().split()) else []
            return {'items': items, 'total': len(items), 'catalogue_total': 1, 'source': 'builtin', 'stale': False, 'error': None, 'fetched_at': None}
        if source != 'cds': raise ValueError('数据来源不存在')
        with self._catalogue_lock:
            cached = self._catalogue_cache
            if cached and time.monotonic() - cached[0] < 3600 and not refresh:
                result = {**copy.deepcopy(cached[1]), 'source': 'cache', 'stale': False}
            else:
                try:
                    result = {'items': fetch_catalogue(), 'source': 'online', 'stale': False,
                              'error': None, 'fetched_at': datetime.now(timezone.utc).isoformat()}
                    self._catalogue_cache = (time.monotonic(), copy.deepcopy(result))
                except Exception:
                    message = '无法更新官方数据集目录，请检查网络后重试；也可手动输入数据集 ID。'
                    result = ({**copy.deepcopy(cached[1]), 'source': 'cache', 'stale': True, 'error': message}
                              if cached else {'items': [], 'source': 'error', 'stale': False,
                                              'error': message, 'fetched_at': None})
        result['catalogue_total'] = len(result['items'])
        words = query.strip().casefold().split()
        result['items'] = [item for item in result['items']
                           if all(word in f"{item['title']} {item['id']}".casefold() for word in words)]
        result['total'] = len(result['items'])
        return result

    def schema(self, dataset_id: str, account: Optional[dict[str, Any]] = None, *, refresh: bool = False, prefix: str = DEFAULT_PREFIX) -> dict[str, Any]:
        if dataset_id == ARCO_ID: raise ValueError('ARCO 本地导出已移除')
        key = (dataset_id, prefix if dataset_id in FILE_MIRROR_IDS else (account or {}).get('url'), (account or {}).get('id') if dataset_id not in MIRROR_IDS else None)
        with self._lock:
            cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < 300 and not refresh:
            return {**copy.deepcopy(cached[1]), 'source': 'cache', 'stale': False}
        try:
            if dataset_id == NCAR_ID:
                schema = ncar_schema(prefix)
            elif dataset_id == GDEX_ID:
                schema = gdex_schema(prefix)
            else:
                if not account or not account.get('key'):
                    raise ValueError('没有可用账号')
                schema = DatastoresProvider(url=account.get('url', 'https://cds.climate.copernicus.eu/api'), key=account['key']).schema(dataset_id)
            result = {**finish_schema(schema), 'source': 'online', 'stale': False, 'error': None,
                      'fetched_at': datetime.now(timezone.utc).isoformat()}
            with self._lock:
                self._cache[key] = (time.monotonic(), copy.deepcopy(result))
            return result
        except Exception as error:
            message = '无法获取在线字段，请检查数据集 ID、可用账号与网络后重试。'
            if isinstance(error, requests.HTTPError) and error.response.status_code == 404:
                message = '该数据集的元数据或表单暂不可用（HTTP 404），请重试或查看官方页面。'
            if dataset_id in MIRROR_IDS:
                message = '无法获取镜像字段，请检查后端网络与 NCAR 目录。'
            if cached:
                return {**copy.deepcopy(cached[1]), 'source': 'cache', 'stale': True, 'error': message}
            return {'collection_id': dataset_id, 'title': dataset_id, 'fields': [],
                    'source': 'error', 'stale': False, 'error': message, 'fetched_at': None, 'support_status': 'unavailable', 'diagnostics': []}

    def by_revision(self, dataset_id: str, revision: str) -> dict:
        with self._lock:
            for _, document in self._cache.values():
                if document['collection_id'] == dataset_id and document.get('revision') == revision:
                    return copy.deepcopy(document)
        raise ValueError('字段定义已更新或服务已重启，请重新获取字段')

    def constraints(self, dataset_id: str, selection: dict[str, Any], account: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if dataset_id == ARCO_ID: raise ValueError('ARCO 本地导出已移除')
        if dataset_id in MIRROR_IDS:
            return {'constraints': {}, 'source': 'not_applicable', 'error': None}
        try:
            if not account or not account.get('key'): raise ValueError('没有可用账号')
            values = DatastoresProvider(url=account.get('url', 'https://cds.climate.copernicus.eu/api'), key=account['key']).constraints(dataset_id, selection)
            return {'constraints': values, 'source': 'online', 'error': None}
        except Exception:
            return {'constraints': {}, 'source': 'error',
                    'error': '约束查询暂不可用；当前仅做本地参数检查，请求是否被 CDS 接受仍需实际请求验证。'}

    def costing(self, dataset_id: str, selection: dict[str, Any], account: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if dataset_id == ARCO_ID: raise ValueError('ARCO 本地导出已移除')
        if dataset_id in MIRROR_IDS:
            return {'source': 'not_applicable', 'error': '此数据来源不提供 CDS 请求规模估算。'}
        if not account or not account.get('key'):
            return {'source': 'error', 'error': '请先添加可用 CDS 账号，再刷新请求规模。'}
        try:
            result = DatastoresProvider(url=account['url'], key=account['key']).estimate_costs(dataset_id, selection)
            # 保留官方规模单位；cost 不是下载文件的字节数。
            cost = result['cost']
            limit = result.get('limit')
            if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
                raise ValueError('无效规模')
            if limit is not None and (isinstance(limit, bool) or not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit < 0):
                raise ValueError('无效上限')
            return {'source': 'online', 'error': None, 'id': result.get('id'), 'cost': cost, 'limit': limit}
        except Exception:
            return {'source': 'error', 'error': '请求规模估算暂不可用，请检查账号、参数与网络后手动重试。'}

    def costing_plan(self, dataset_id: str, selections: list[dict[str, Any]], account: Optional[dict[str, Any]]) -> dict[str, Any]:
        if not account or not account.get('key'):
            return {**self.costing(dataset_id, selections[0], account), 'request_count': len(selections), 'estimated_count': 0}

        with ThreadPoolExecutor(max_workers=min(4, len(selections))) as executor:
            results = list(executor.map(lambda selection: self.costing(dataset_id, selection, account), selections))

        estimated = [(index, result) for index, result in enumerate(results, 1) if result['source'] == 'online']
        summary = {
            'request_count': len(selections),
            'estimated_count': len(estimated),
            'over_limit_count': sum(result['limit'] is not None and result['cost'] > result['limit'] for _, result in estimated),
        }
        if len(estimated) != len(results):
            return {**summary, 'source': 'error',
                    'error': f'已估算 {len(estimated)}/{len(results)} 个子请求，无法确定最大规模。请手动重试。'}
        index, largest = max(estimated, key=lambda item: item[1]['cost'])
        return {**largest, **summary, 'max_index': index}
