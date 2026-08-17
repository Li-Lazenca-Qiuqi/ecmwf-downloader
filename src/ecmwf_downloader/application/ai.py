"""Optional OpenAI-compatible request suggestion service.

The adapter lives in the new package so the installed wheel does not depend
on the retired ``src.core`` modules.  The optional ``openai`` package is only
imported when a suggestion is requested.
"""

from __future__ import annotations

import json
from typing import Any

from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.infrastructure.secrets import SecretStore


class AIService:
    def __init__(self, settings: AppSettings, secrets: SecretStore):
        self.settings = settings
        self.secrets = secrets

    def suggest(self, field_schema: dict[str, Any], user_request: str) -> dict[str, Any]:
        config = {
            "enabled": False,
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 4096,
            "timeout": 120,
            **self.settings.ai,
            **self.secrets.ai_config(),
        }
        if not config.get("enabled"):
            raise RuntimeError("AI 功能未启用")
        if not config.get("api_key"):
            raise RuntimeError("AI API Key 未配置，请使用 ecmwf config set-ai-key")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("AI 功能需要安装可选依赖 openai，请运行 uv sync --extra ai") from exc

        system_prompt = (
            "你是 ECMWF CDS 请求参数助手。根据给定字段 schema 和用户需求，"
            "只返回可以直接作为 request_payload 的 JSON 对象，不要 Markdown、解释或额外字段。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"field_schema": field_schema, "user_request": user_request},
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            client = OpenAI(
                api_key=str(config["api_key"]),
                base_url=str(config.get("base_url") or "https://api.openai.com/v1"),
                timeout=float(config.get("timeout", 120)),
            )
            response = client.chat.completions.create(
                model=str(config.get("model") or "gpt-4o-mini"),
                messages=messages,
                temperature=float(config.get("temperature", 0.3)),
                max_tokens=int(config.get("max_tokens", 4096)),
            )
            content = response.choices[0].message.content if response.choices else ""
        except Exception as exc:
            raise RuntimeError(f"AI API 调用失败: {exc}") from exc

        if not content:
            raise RuntimeError("AI 返回空响应")
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].lstrip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("AI 返回的不是有效 JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("AI 返回必须是 JSON 对象")
        return result
