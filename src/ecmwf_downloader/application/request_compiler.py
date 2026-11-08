"""按字段结构编译请求；界面选择与实际 API 参数分别处理。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
import re
from typing import Any


@dataclass
class CompileResult:
    request_payload: dict[str, Any]
    errors: list[str]

    def checked(self) -> dict[str, Any]:
        if self.errors:
            raise ValueError('；'.join(self.errors))
        return self.request_payload


def validate_value(field: dict, value: Any) -> None:
    kind = field['field_type']
    def numeric(item):
        return type(item) is int or type(item) is float and math.isfinite(item)
    if kind == 'unsupported':
        raise ValueError('此字段暂未支持')
    if kind == 'number':
        if not numeric(value) or field.get('integer') and type(value) is not int:
            raise ValueError('需要有限数值' if not field.get('integer') else '需要整数')
        if field.get('minimum') is not None and value < field['minimum'] or field.get('maximum') is not None and value > field['maximum']:
            raise ValueError('数值超出允许范围')
    elif kind == 'boolean':
        if type(value) is not bool:
            raise ValueError('需要布尔值')
    elif kind == 'text':
        if not isinstance(value, str):
            raise ValueError('需要文本')
    elif kind == 'choice':
        if type(value) not in {str, bool} and not numeric(value):
            raise ValueError('请选择一个有效值')
    elif kind == 'object':
        if not isinstance(value, dict):
            raise ValueError('需要结构化对象')
        properties = field['properties']
        for key in value:
            if key not in properties:
                raise ValueError(f'对象中没有字段 {key}')
            validate_value(properties[key], value[key])
        if any(child['required'] and key not in value for key, child in properties.items()):
            raise ValueError('请补齐对象中的必填字段')
    elif kind == 'multiple':
        if not isinstance(value, list) or any(type(item) not in {str, int, float, bool} or type(item) is float and not math.isfinite(item) for item in value):
            raise ValueError('需要有效的选项数组')
        if field.get('integer') and any(type(item) is not int for item in value):
            raise ValueError('需要整数数组')
        if field.get('item_type') in {'number', 'boolean'}:
            if any(not numeric(item) if field['item_type'] == 'number' else type(item) is not bool for item in value):
                raise ValueError('数组元素类型不正确')
    elif kind in {'area', 'location'}:
        count = 4 if kind == 'area' else 2
        if not isinstance(value, list) or len(value) != count or not all(numeric(item) for item in value):
            raise ValueError('请填写完整且有效的坐标')
        bounds = field.get('bounds', {})
        limits = bounds.get('range', {'n': 90, 'w': -180, 's': -90, 'e': 180})
        n, w, s, e = value if kind == 'area' else [value[0], value[1], value[0], value[1]]
        if not limits['s'] <= s <= n <= limits['n'] or not all(limits['w'] <= longitude <= limits['e'] for longitude in [w, e]):
            raise ValueError('坐标超出数据集允许范围或南北顺序错误')
        if kind == 'area':
            span = {'lat': n - s, 'lon': (e - w) if e >= w else e - w + 360}
            for limit, compare in [('minimum_extent', lambda a, b: a < b), ('maximum_extent', lambda a, b: a > b)]:
                if any(compare(span[axis], number) and not math.isclose(span[axis], number, rel_tol=0, abs_tol=1e-9) for axis, number in bounds.get(limit, {}).items()):
                    raise ValueError('区域大小不符合数据集限制')
    elif kind == 'date_range':
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError('请填写开始和结束日期')
        start, end = value
        try:
            date.fromisoformat(start if len(start) == 10 else start + '-01')
            date.fromisoformat(end if len(end) == 10 else end + '-01')
        except (ValueError, TypeError):
            raise ValueError('日期格式无效') from None
        bounds = field.get('bounds', {})
        if start > end or start < bounds['minStart'][:len(start)] or end > bounds['maxEnd'][:len(end)]:
            raise ValueError('日期起止顺序或可用范围不正确')
    if field.get('options'):
        selected = value if kind == 'multiple' else [value]
        options = {json.dumps(option['value'], sort_keys=True) for option in field['options']}
        if any(json.dumps(item, sort_keys=True) not in options for item in selected):
            raise ValueError('所选值不在数据集选项中')
    spec = field.get('json_schema') or {}
    for lower, upper in [('minItems', 'maxItems')] if isinstance(value, list) else [('minLength', 'maxLength')] if isinstance(value, str) else []:
        if lower in spec and len(value) < spec[lower] or upper in spec and len(value) > spec[upper]:
            raise ValueError('输入长度不符合字段限制')
    if isinstance(value, str) and 'pattern' in spec and re.search(spec['pattern'], value) is None:
        raise ValueError('文本格式不符合字段要求')


def compile_request(schema: dict, values: dict[str, Any], *, complete: bool = True, wire: bool = False) -> CompileResult:
    fields = {field['name']: field for field in schema['fields']}
    errors = [item['message'] for item in schema.get('diagnostics', []) if item['blocking']]
    if errors:
        return CompileResult({}, errors)
    errors.extend(f'{name}：数据集中不存在此字段' for name in values if name not in fields)
    children = {child for field in fields.values() for child in field.get('children', [])}
    payload = {}
    def visit(name: str, branch_required: bool = False):
        field = fields[name]
        kind = field['field_type']
        if kind == 'exclusive':
            explicit = [child for child in field['children'] if child in values]
            selected = values.get(name)
            if selected is None:
                if len(explicit) > 1:
                    errors.append(f'{field["label"]}：只能选择一个分支')
                    return
                selected = explicit[0] if explicit else field.get('default')
            if selected not in field['children']:
                if complete:
                    errors.append(f'{field["label"]}：请选择一个分支')
                return
            visit(selected, True)
            return
        if kind == 'layout':
            for child in field['children']:
                visit(child, branch_required)
            return
        if not field['request_field']:
            return
        value = values.get(name)
        if value is None or value == '' or value == []:
            if complete and (field['required'] or branch_required):
                errors.append(f'{field["label"]}：请填写必填参数')
            return
        if wire and kind == 'location' and isinstance(value, dict):
            if set(value) != {'latitude', 'longitude'}:
                errors.append(f'{field["label"]}：单点需要 latitude 和 longitude')
                return
            value = [value['latitude'], value['longitude']]
        if wire and kind == 'date_range' and isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
            value = value[0].split('/')
        if wire and kind == 'choice' and field.get('wire_type') == 'array' and isinstance(value, list) and len(value) == 1:
            value = value[0]
        try:
            validate_value(field, value)
        except (ValueError, TypeError) as error:
            errors.append(f'{field["label"]}：{error}')
            return
        if kind == 'date_range':
            value = ['/'.join(value)]
        elif kind == 'location':
            value = {'latitude': value[0], 'longitude': value[1]}
        elif kind == 'multiple':
            value = list({json.dumps(item, sort_keys=True): item for item in value}.values())
        elif kind == 'choice' and field.get('wire_type') == 'array':
            value = [value]
        payload[name] = value
    for name in schema.get('roots', [name for name in fields if name not in children]):
        visit(name)
    return CompileResult(payload, errors)
