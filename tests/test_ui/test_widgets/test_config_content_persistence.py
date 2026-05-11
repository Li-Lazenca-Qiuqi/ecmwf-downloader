"""配置保存/加载（新格式）测试。"""

from src.core.dataset_schema import DynamicFormField, FieldType, FormFieldDefinition
from src.ui.pages.create_task.mappers import FormConfigMapper


class TestFormConfigMapperPersistence:
    """验证配置文件的新格式序列化与反序列化。"""

    def test_serialize_field_config_compact_schema(self):
        field = DynamicFormField(
            definition=FormFieldDefinition(
                name="licences",
                label="许可证",
                field_type=FieldType.LICENCE,
                required=True,
                details={
                    "name": "licences",
                    "type": "LicenceWidget",
                    "details": {"licences": [{"id": "lic1", "label": "L1"}]},
                    "extra_set": {"b", "a"},
                },
            ),
            values=["lic1"],
            selected=["lic1"],
        )

        info = FormConfigMapper.serialize_field(field)

        assert set(info.keys()) == {"field_type", "selected", "definition"}
        assert info["field_type"] == "licence"
        assert info["selected"] == ["lic1"]
        assert info["definition"]["type"] == "LicenceWidget"
        assert info["definition"]["extra_set"] == ["a", "b"]

    def test_deserialize_keeps_special_widget_type_consistent(self):
        field_info = {
            "field_type": "exclusive_group",
            "selected": ["global"],
            "definition": {
                "name": "area_group",
                "label": "Geographical area",
                "required": False,
                "type": "ExclusiveGroupWidget",
                "children": ["global", "area"],
                "details": {"default": "global"},
            },
        }

        state = FormConfigMapper.deserialize_field("area_group", field_info)

        assert state.field_type == FieldType.EXCLUSIVE_GROUP
        assert state.selected == ["global"]
        assert state.definition.details["type"] == "ExclusiveGroupWidget"

    def test_deserialize_uses_definition_values_for_product_type(self):
        """加载时 product_type 应恢复 definition 里的完整可选项。"""
        field_info = {
            "field_type": "string_array",
            "selected": [],
            "definition": {
                "name": "product_type",
                "label": "Product type",
                "required": True,
                "type": "StringListWidget",
                "details": {
                    "values": [
                        "reanalysis",
                        "ensemble_members",
                        "ensemble_mean",
                        "ensemble_spread",
                    ]
                },
            },
        }

        state = FormConfigMapper.deserialize_field("product_type", field_info)

        assert state.field_type == FieldType.STRING_ARRAY
        assert state.values == [
            "reanalysis",
            "ensemble_members",
            "ensemble_mean",
            "ensemble_spread",
        ]
