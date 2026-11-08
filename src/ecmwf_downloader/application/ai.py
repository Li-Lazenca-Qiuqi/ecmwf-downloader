"""Optional OpenAI-compatible request suggestion service.

The adapter lives in the new package so the installed wheel does not depend
on the retired ``src.core`` modules.  The optional ``openai`` package is only
imported when a suggestion is requested.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
from typing import Any

from ecmwf_downloader.application.request_compiler import validate_value
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.infrastructure.secrets import SecretStore


class AIService:
    def __init__(self, settings: AppSettings, secrets: SecretStore):
        self.settings = settings
        self.secrets = secrets

    def _config(self) -> dict[str, Any]:
        secrets = self.secrets.ai_config()
        config = {
            "enabled": False,
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 4096,
            "timeout": 120,
            "json_mode": True,
            **secrets,
            **self.settings.ai,
        }
        # 密钥始终来自凭据存储，公共配置不作为密钥来源。
        config['api_key'] = secrets.get('api_key')
        return config

    def configuration(self) -> dict[str, Any]:
        config = self._config()
        sdk_available = importlib.util.find_spec('openai') is not None
        return {**{name: config[name] for name in ['enabled', 'base_url', 'model', 'json_mode']},
                'has_api_key': bool(config.get('api_key')), 'sdk_available': sdk_available,
                'ready': bool(config.get('enabled') and config.get('api_key') and sdk_available)}

    def suggest(self, field_schema: dict[str, Any], user_request: str) -> dict[str, Any]:
        config = self._config()
        if not user_request.strip():
            raise RuntimeError('请先填写下载需求')
        if not config.get("enabled"):
            raise RuntimeError("AI 功能未启用")
        if not config.get("api_key"):
            raise RuntimeError("AI API Key 未配置，请使用 ecmwf config set-ai-key")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("AI 功能需要安装可选依赖 openai，请运行 uv sync --extra ai") from exc

        fields = [field for field in field_schema.get('fields', []) if field.get('request_field', True) or field.get('field_type') == 'exclusive']
        if not fields:
            raise RuntimeError('请先获取数据集字段，再补全参数')
        compact_schema = {name: field_schema[name] for name in ['collection_id', 'title', 'current_selection'] if name in field_schema}
        compact_schema['fields'] = [{**{name: field[name] for name in [
            'name', 'label', 'field_type', 'required', 'default', 'integer', 'item_type', 'minimum', 'maximum', 'children', 'titles', 'bounds', 'properties'
        ] if name in field}, 'options': [{'value': option['value'], 'label': option.get('label', str(option['value']))}
                                        for option in field.get('options', [])]} for field in fields]
        system_prompt = (
            "你是 ECMWF CDS 请求参数助手。根据给定字段 schema 和用户需求，"
            "只返回符合界面字段定义的 JSON 建议对象，不要 Markdown、解释或额外字段。"
            "基于 current_selection 补全或按需求修改参数，未提及的已选参数保持不变。"
            "只能使用 schema 中的字段名称和选项 value，不要使用显示名称，不得编造变量或时间。"
            "multiple 字段返回数组，choice 返回单值，number/boolean 保持原始类型，area 返回 [North, West, South, East] 数字数组。"
            "date_range 返回 [开始日期, 结束日期]；location 返回 [Latitude, Longitude]。切换互斥分支时同时返回 exclusive 字段及其 children 中的分支名，只返回该分支参数。只生成有依据的参数，需求未明确且没有默认值的字段不填写。输出目录和拆分策略不是请求参数，不要返回。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"field_schema": compact_schema, "user_request": user_request},
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            with OpenAI(
                api_key=str(config["api_key"]),
                base_url=str(config.get("base_url") or "https://api.openai.com/v1"),
                timeout=float(config.get("timeout", 120)),
                max_retries=0,
            ) as client:
                response = client.chat.completions.create(
                    model=str(config.get("model") or "gpt-4o-mini"),
                    messages=messages,
                    temperature=float(config.get("temperature", 0.3)),
                    max_tokens=int(config.get("max_tokens", 4096)),
                    **({'response_format': {'type': 'json_object'}} if config.get('json_mode') else {}),
                )
                choice = response.choices[0] if response.choices else None
                if choice and choice.finish_reason == 'length':
                    raise RuntimeError('AI 响应不完整，请缩小请求范围后重试')
                content = choice.message.content if choice else ''
        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc).startswith('AI 响应不完整'):
                raise RuntimeError('AI 响应不完整，请缩小请求范围后重试') from None
            message = {'AuthenticationError': 'AI 认证失败，请检查 API Key',
                       'PermissionDeniedError': 'AI 服务拒绝访问，请检查账号权限和模型',
                       'RateLimitError': 'AI 服务额度不足或请求过于频繁，请稍后重试',
                       'APITimeoutError': 'AI 请求超时，请稍后重试',
                       'APIConnectionError': '无法连接 AI 服务，请检查服务地址与网络',
                       'BadRequestError': 'AI 服务不接受当前模型或请求参数，请检查配置；兼容服务可尝试关闭 JSON 模式'}.get(type(exc).__name__, 'AI 服务调用失败，请检查配置或稍后重试')
            raise RuntimeError(message) from None

        if not content:
            raise RuntimeError("AI 返回空响应")
        content = content.strip()
        content = re.sub(r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', content, flags=re.IGNORECASE)
        def reject_constant(_value: str) -> None:
            raise ValueError('JSON 不允许非有限数值')
        try:
            result = json.loads(content, parse_constant=reject_constant)
        except (json.JSONDecodeError, ValueError):
            raise RuntimeError("AI 返回的不是有效 JSON，请调整需求后重试") from None
        if not isinstance(result, dict):
            raise RuntimeError("AI 返回必须是 JSON 对象")
        for wrapper in ['parameters', 'request_payload']:
            if set(result) == {wrapper} and isinstance(result[wrapper], dict) and not any(field['name'] == wrapper for field in fields):
                result = result[wrapper]
        self._validate(result, fields)
        if not result:
            raise RuntimeError('AI 未给出可用参数，请补充变量、时间或区域信息')
        return result

    @staticmethod
    def _validate(parameters: dict[str, Any], fields: list[dict[str, Any]]) -> None:
        by_name = {field['name']: field for field in fields}
        for name, value in parameters.items():
            field = by_name.get(name)
            if field is None:
                raise RuntimeError('AI 返回了当前数据集中不存在的字段，未应用建议')
            try:
                if field['field_type'] == 'exclusive':
                    if value not in field['children']:
                        raise ValueError('分支不存在')
                else:
                    validate_value(field, value)
            except (ValueError, TypeError):
                raise RuntimeError(f"AI 返回的 {field.get('label', name)} 参数类型、选项或范围不正确，未应用建议") from None
