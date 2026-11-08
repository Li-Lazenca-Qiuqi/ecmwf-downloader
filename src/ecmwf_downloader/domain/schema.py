"""字段定义、分组和来源能力的统一表示。"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, TypedDict


class GroupSpec(TypedDict):
    name: str
    label: str
    kind: str
    children: list[str]
    default: str | None
    titles: dict[str, str]


def finish_schema(document: dict[str, Any]) -> dict[str, Any]:
    """保留原字段定义，并建立可编译的结构与内容标识。"""
    result = deepcopy(document)
    fields = result['fields']
    by_name = {field['name']: field for field in fields}
    groups: list[GroupSpec] = [
        {'name': field['name'], 'label': field['label'], 'kind': field['field_type'],
         'children': field['children'], 'default': field.get('default'), 'titles': field.get('titles', {})}
        for field in fields if field.get('children')
    ]
    diagnostics = []
    if len(by_name) != len(fields):
        diagnostics.append({'code': 'duplicate_field', 'field': '', 'message': '表单存在重复字段标识', 'blocking': True})
    for group in groups:
        for name in group['children']:
            if name not in by_name:
                diagnostics.append({'code': 'missing_reference', 'field': group['name'], 'message': f'分组引用的字段不存在：{name}', 'blocking': True})
    visiting, visited = set(), set()
    def visit(name: str) -> None:
        if name in visiting:
            diagnostics.append({'code': 'cyclic_group', 'field': name, 'message': '表单分组存在循环引用', 'blocking': True})
            return
        if name in visited or name not in by_name:
            return
        visiting.add(name)
        for child in by_name[name].get('children', []):
            visit(child)
        visiting.remove(name)
        visited.add(name)
    for name in by_name:
        visit(name)
    def inspect_fields(items, prefix=''):
        for field in items:
            yield field, prefix + field['name']
            yield from inspect_fields(field.get('properties', {}).values(), prefix + field['name'] + '.')
    for field, path in inspect_fields(fields):
        if field.get('field_type') == 'unsupported':
            diagnostics.append({'code': 'unsupported_widget', 'field': path, 'message': f'{field["label"]} 的控件暂未支持', 'blocking': False})
    child_names = {child for group in groups for child in group['children']}
    result['groups'] = groups
    result['roots'] = [field['name'] for field in fields if field['name'] not in child_names]
    result['diagnostics'] = diagnostics
    result['support_status'] = 'unavailable' if not fields or any(d['blocking'] for d in diagnostics) else 'partial' if diagnostics else 'full'
    names = {field['name'] for field in fields if field.get('request_field')}
    splits = ['none']
    for strategy, required in [('year', {'year'}), ('month', {'year', 'month'}), ('day', {'year', 'month', 'day'})]:
        if required <= names and not any(f.get('field_type') == 'date_range' for f in fields):
            splits.append(strategy)
    result['capabilities'] = {'split_strategies': splits, 'file_selection': 'object_key' in names,
                              'spatial_modes': [field['field_type'] for field in fields if field['field_type'] in {'area', 'location'}]}
    content = json.dumps({'dataset': result['collection_id'], 'fields': fields, 'groups': groups}, sort_keys=True, ensure_ascii=False)
    result['revision'] = hashlib.sha256(content.encode()).hexdigest()[:24]
    return result
