"""Small adapter around the official ``ecmwf-datastores-client`` package."""

from __future__ import annotations

from typing import Any


class DatastoresProvider:
    def __init__(self, *, url: str, key: str):
        try:
            from ecmwf.datastores import Client
        except ImportError as exc:  # pragma: no cover - dependency is installed in the wheel
            raise RuntimeError("ecmwf-datastores-client 未安装") from exc
        self.client = Client(url=url, key=key)

    def schema(self, dataset_id: str) -> dict[str, Any]:
        collection = self.client.get_collection(dataset_id)
        fields = self._fields(collection)
        return {
            "collection_id": dataset_id,
            "title": getattr(collection, "title", dataset_id),
            "description": getattr(collection, "description", ""),
            "fields": fields,
            "constraints": self._constraints(collection),
        }

    def constraints(self, dataset_id: str, selection: dict[str, Any]) -> dict[str, list[str]]:
        result = self.client.apply_constraints(dataset_id, selection)
        return self._normalise_constraints(result)

    @classmethod
    def _fields(cls, collection: Any) -> list[dict[str, Any]]:
        form = getattr(collection, "form", None)
        raw_fields: list[tuple[str, dict[str, Any]]] = []
        if isinstance(form, list):
            raw_fields = [
                (str(item.get("name")), item)
                for item in form
                if isinstance(item, dict) and item.get("name")
            ]
        elif isinstance(form, dict):
            raw_fields = [
                (str(name), item)
                for name, item in form.items()
                if isinstance(item, dict)
            ]
        if not raw_fields:
            data = getattr(collection, "json", {})
            form_data = data.get("form", data.get("request", {})) if isinstance(data, dict) else {}
            properties = form_data.get("properties", form_data.get("fields", {})) if isinstance(form_data, dict) else {}
            if isinstance(properties, dict):
                raw_fields = [(str(name), item) for name, item in properties.items() if isinstance(item, dict)]
        return [cls._field(name, item) for name, item in raw_fields]

    @classmethod
    def _field(cls, name: str, raw: dict[str, Any]) -> dict[str, Any]:
        schema = raw.get("schema") if isinstance(raw.get("schema"), dict) else {}
        values = cls._values(raw)
        value_type = schema.get("type") or raw.get("type") or "string"
        if value_type == "array":
            field_type = "integer_list" if (schema.get("items") or {}).get("type") == "integer" else "string_list"
        elif value_type == "integer":
            field_type = "integer_single"
        elif value_type in {"number", "float"}:
            field_type = "number"
        elif value_type == "boolean":
            field_type = "boolean"
        else:
            field_type = "string_single"
        return {
            "name": name,
            "label": name,
            "field_type": field_type,
            "required": bool(raw.get("required", False)),
            "values": values,
        }

    @staticmethod
    def _values(raw: dict[str, Any]) -> list[str]:
        details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
        schema = raw.get("schema") if isinstance(raw.get("schema"), dict) else {}
        values = details.get("values") or schema.get("enum")
        if isinstance(values, list):
            return [str(value) for value in values if value is not None]
        return []

    @classmethod
    def _constraints(cls, collection: Any) -> dict[str, list[str]]:
        return cls._normalise_constraints(getattr(collection, "constraints", {}))

    @staticmethod
    def _normalise_constraints(raw: Any) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if not isinstance(item, dict):
                continue
            for name, values in item.items():
                if isinstance(values, list):
                    existing = result.setdefault(str(name), [])
                    for value in values:
                        value = str(value)
                        if value not in existing:
                            existing.append(value)
        return result
