"""将官方 CDS 表单统一为完整、带类型的请求字段。"""

from __future__ import annotations

import html
import re
from typing import Any
from ecmwf_downloader.config import service_url
from ecmwf_downloader.domain.schema import finish_schema


def plain_text(value: Any) -> str:
    return html.unescape(re.sub(r'<[^>]+>', ' ', str(value or ''))).strip()


class DatastoresProvider:
    def __init__(self, *, url: str, key: str):
        from ecmwf.datastores import Client
        self.client = Client(url=service_url(url), key=key, timeout=(10, 25), maximum_tries=1,
                             progress=False, log_callback=lambda *args: None)

    def schema(self, dataset_id: str) -> dict[str, Any]:
        collection = self.client.get_collection(dataset_id)
        return finish_schema({'collection_id': dataset_id, 'source_id': 'cds', 'title': collection.title,
                'description': plain_text(collection.description), 'fields': self._fields(collection)})

    def constraints(self, dataset_id: str, selection: dict[str, Any]) -> dict[str, list[Any]]:
        return self._normalise_constraints(self.client.apply_constraints(dataset_id, selection))

    def estimate_costs(self, dataset_id: str, selection: dict[str, Any]) -> dict[str, Any]:
        return self.client.estimate_costs(dataset_id, selection)

    @classmethod
    def _fields(cls, collection: Any) -> list[dict[str, Any]]:
        form = collection.form
        if isinstance(form, dict):
            required = form.get('required', [])
            properties = form.get('properties', form.get('fields', form))
            form = [{**item, 'name': name, 'schema': item, 'required': name in required or item.get('required') is True}
                    for name, item in properties.items() if isinstance(item, dict)]
        if not isinstance(form, list):
            raise ValueError('数据集表单格式不受支持')
        result = []
        for item in form:
            if not isinstance(item, dict):
                continue
            children = item.get('children') or item.get('fields')
            if isinstance(children, list) and any(isinstance(child, dict) for child in children):
                # 布局分组可嵌套字段；组内所有参数仍完整返回。
                class Group:
                    form = children
                result.extend(cls._fields(Group()))
            name = item.get('name') or item.get('id')
            if name:
                result.append(cls._field(str(name), item))
        if not result:
            raise ValueError('数据集没有可识别的字段')
        return result

    @classmethod
    def _field(cls, name: str, raw: dict[str, Any]) -> dict[str, Any]:
        details = raw.get('details') if isinstance(raw.get('details'), dict) else {}
        schema = raw.get('schema') if isinstance(raw.get('schema'), dict) else raw
        widget = str(raw.get('type', 'string'))
        value_type = schema.get('type', 'string')
        options: list[dict[str, Any]] = []
        seen: dict[str, dict[str, Any]] = {}
        import json
        def add_options(section: dict, group: str = '') -> None:
            values = section.get('values', section.get('enum', []))
            labels = section.get('labels', {})
            if isinstance(values, dict):
                labels = {**values, **labels}
                values = list(values)
            if isinstance(values, list):
                for value in values:
                    label = labels.get(str(value), str(value))
                    if isinstance(value, dict):
                        label = value.get('label', value.get('value', ''))
                        value = value.get('value')
                    marker = json.dumps(value, sort_keys=True)
                    if value is None:
                        continue
                    if marker not in seen:
                        option = {'value': value, 'label': plain_text(label), 'group': group,
                                  'groups': [group] if group else []}
                        seen[marker] = option
                        options.append(option)
                    elif group and group not in seen[marker]['groups']:
                        # 请求值只保留一份，分类关系完整保留，兼容原有首个 group 字段。
                        seen[marker]['groups'].append(group)
                        if not seen[marker]['group']:
                            seen[marker]['group'] = group
            for child in section.get('groups', []):
                if isinstance(child, dict): add_options(child, plain_text(child.get('label', group)))
        add_options(details)
        add_options(schema.get('items', {}) if value_type == 'array' else schema)
        informational = widget in {'ExclusiveGroupWidget', 'ExclusiveGroupAccordionWidget', 'GroupWidget', 'FreeEditionWidget', 'LicenceWidget', 'HeadingWidget'}
        if widget in {'ExclusiveGroupWidget', 'ExclusiveGroupAccordionWidget'}:
            field_type = 'exclusive'
        elif widget == 'GroupWidget':
            field_type = 'layout'
        elif informational:
            field_type = 'info'
        elif widget == 'GeographicExtentWidget':
            field_type = 'area'
        elif widget == 'GeographicLocationWidget':
            field_type = 'location'
        elif widget == 'DateRangeWidget':
            field_type = 'date_range'
        elif value_type == 'object' and 'properties' in schema:
            field_type = 'object'
        elif widget in {'StringListWidget', 'StringListArrayWidget'} or value_type == 'array':
            field_type = 'multiple'
        elif widget == 'StringChoiceWidget':
            field_type = 'choice'
        elif value_type in {'integer', 'number', 'float'}:
            field_type = 'number'
        elif value_type == 'boolean' or widget == 'BooleanWidget':
            field_type = 'boolean'
        elif widget in {'string', 'StringWidget', 'TextWidget'}:
            field_type = 'choice' if options else 'text'
        else:
            field_type = 'unsupported'
        if any(key in schema for key in ['oneOf', 'anyOf', 'allOf', '$ref', 'if']):
            field_type = 'unsupported'
        if field_type == 'multiple' and schema.get('items', {}).get('type') in {'object', 'array'}:
            field_type = 'unsupported'
        default = details.get('default', schema.get('default'))
        if isinstance(default, list):
            unique = {}
            for item in default: unique.setdefault(json.dumps(item, sort_keys=True), item)
            default = list(unique.values())
            if field_type == 'choice': default = default[0] if default else None
        if field_type == 'area' and isinstance(default, dict):
            default = [default.get('n', 90), default.get('w', -180), default.get('s', -90), default.get('e', 180)]
        if field_type == 'location' and isinstance(default, dict):
            default = [default['lat'], default['lon']]
        if field_type == 'date_range':
            default = [details.get('defaultStart'), details.get('defaultEnd')]
        if widget == 'LicenceWidget':
            description = '请在 CDS 数据集页面确认并接受所需条款；本工具不会替你接受条款。'
        else:
            description = plain_text(raw.get('help') or details.get('help') or details.get('text') or raw.get('description'))
        children = raw.get('children') or raw.get('fields') or []
        return {'name': name, 'label': plain_text(raw.get('label', name)), 'field_type': field_type,
                'widget': widget, 'required': raw.get('required') is True,
                'options': options, 'values': [option['value'] for option in options],
                'default': default, 'description': description, 'request_field': not informational,
                'integer': value_type == 'integer' or (value_type == 'array' and schema.get('items', {}).get('type') == 'integer'),
                'item_type': schema.get('items', {}).get('type', 'string') if value_type == 'array' else 'string',
                'minimum': schema.get('minimum'), 'maximum': schema.get('maximum'),
                'step': details.get('stepX', 1 if value_type == 'integer' else 'any'),
                'children': [child if isinstance(child, str) else child.get('name', child.get('id')) for child in children],
                'titles': details.get('titles', {}),
                'bounds': {key: details[key] for key in ['range', 'minimum_extent', 'maximum_extent', 'stepX', 'stepY', 'minStart', 'maxEnd', 'time_resolution'] if key in details},
                'wire_type': schema.get('type') if schema.get('type') in {'array', 'number', 'integer', 'boolean', 'string'} else None,
                'codec_id': {'date_range': 'cds.date_interval', 'location': 'cds.location_object', 'area': 'coordinates.nwse'}.get(field_type, 'identity'),
                'json_schema': schema if value_type in {'object', 'array'} and not widget.endswith('Widget') else None,
                'open_groups': details.get('accordionOptions', {}).get('openGroups', []),
                'licences': details.get('licences', []),
                'properties': {key: cls._field(key, {**value, 'schema': value, 'required': key in schema.get('required', [])}) for key, value in schema.get('properties', {}).items()}}

    @staticmethod
    def _normalise_constraints(raw: Any) -> dict[str, list[Any]]:
        result: dict[str, list[Any]] = {}
        for item in raw if isinstance(raw, list) else [raw]:
            if not isinstance(item, dict): continue
            for name, values in item.items():
                if isinstance(values, list):
                    target = result.setdefault(str(name), [])
                    for value in values:
                        if value not in target: target.append(value)
        return result
