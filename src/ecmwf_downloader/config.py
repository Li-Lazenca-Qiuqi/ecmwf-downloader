"""Application and filesystem configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Dict, Literal, Optional, Self
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError, field_validator, model_validator

from ecmwf_downloader.infrastructure.yaml_file import atomic_write_yaml, file_write_lock


class SettingsError(ValueError):
    pass


class SettingsIOError(RuntimeError):
    pass


def service_url(value: str) -> str:
    value = value.strip().rstrip('/')
    try:
        url = urlsplit(value)
        _ = url.port
        if (url.scheme in {'http', 'https'} and url.hostname and url.username is None
                and url.password is None and not url.query and not url.fragment):
            return value
    except ValueError:
        pass
    raise ValueError('服务地址需要是无凭据的 HTTP 或 HTTPS URL')


def public_service_url(value: str) -> str:
    try:
        return service_url(value)
    except ValueError:
        # 旧配置可能含 URL 凭据，公开展示时隐藏原值，留待用户更新。
        return ''


class PublicAISettings(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool = False
    base_url: str = 'https://api.openai.com/v1'
    model: str = Field(default='gpt-4o-mini', min_length=1, max_length=200)
    temperature: float = Field(default=0.3, ge=0, le=2)
    timeout: FiniteFloat = Field(default=120, gt=0)
    max_tokens: int = Field(default=4096, gt=0)
    json_mode: bool = True

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return service_url(value)

    @field_validator('model')
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('模型名称不能为空')
        return value.strip()


def public_ai_settings(values: dict[str, Any]) -> dict[str, Any]:
    public = {name: values[name] for name in PublicAISettings.model_fields if name in values}
    if isinstance(public.get('base_url'), str):
        public['base_url'] = public_service_url(public['base_url'])
    return public


class RequestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_workers: int = Field(default=4, ge=1, le=32, strict=True)
    max_retries: int = Field(default=3, ge=0, le=20, strict=True)
    retry_delays: list[Annotated[FiniteFloat, Field(ge=0, strict=True)]] = Field(default_factory=lambda: [5.0, 15.0, 60.0], min_length=1)
    poll_interval: float = Field(default=5, ge=1, le=3600, strict=True, allow_inf_nan=False)


def network_proxy_url(value: str) -> str:
    try:
        address = service_url(value)
        if not urlsplit(address).path and not any(char.isspace() for char in address):
            return address
    except ValueError:
        pass
    raise ValueError('代理地址需要是无凭据的 HTTP(S) 地址，例如 http://主机:端口。')


class NetworkProxySettings(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    mode: Literal['direct', 'system', 'manual'] = 'system'
    url: str = ''

    @field_validator('url')
    @classmethod
    def validate_url(cls, value: str) -> str:
        return network_proxy_url(value) if value.strip() else ''

    @model_validator(mode='after')
    def require_enabled_url(self) -> Self:
        if self.mode == 'manual' and not self.url:
            raise ValueError('手动代理需要填写地址。')
        return self


class AppSettings(BaseModel):
    """Non-secret settings persisted in ``config/app.yaml``."""

    database_path: Path = Path("data/ecmwf.sqlite3")
    config_dir: Path = Path("config")
    requests: RequestSettings = Field(default_factory=RequestSettings)
    ai: Dict[str, Any] = Field(default_factory=dict)
    network_proxy: NetworkProxySettings = Field(default_factory=NetworkProxySettings)

    @field_validator("database_path", "config_dir", mode="before")
    @classmethod
    def expand_paths(cls, value: Any) -> Path:
        return Path(os.path.expandvars(os.path.expanduser(str(value))))

    def resolve_relative_paths(self, base_dir: Optional[Path] = None) -> "AppSettings":
        base = (base_dir or Path.cwd()).resolve()
        values = self.model_dump()
        for key in ("database_path", "config_dir"):
            path = Path(values[key])
            values[key] = path if path.is_absolute() else base / path
        return AppSettings.model_validate(values)


DEFAULT_APP_CONFIG: dict[str, Any] = {
    "database_path": "data/ecmwf.sqlite3",
    "config_dir": "config",
    "requests": {
        "max_workers": 4,
        "max_retries": 3,
        "retry_delays": [5, 15, 60],
        "poll_interval": 5,
    },
    "ai": {
        "enabled": False,
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "timeout": 120,
    },
}


def read_app_config(path: Path) -> dict[str, Any]:
    try:
        return parse_app_config(path.read_bytes())
    except OSError:
        raise SettingsIOError("无法读取应用配置，请检查文件权限。") from None


def parse_app_config(content: bytes) -> dict[str, Any]:
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError):
        raise SettingsError("无法读取应用配置，请检查 YAML 格式。") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SettingsError("应用配置必须是 YAML 对象。")
    legacy_proxy = data.pop('cds_proxy', None)
    if legacy_proxy is not None and 'network_proxy' not in data:
        if not isinstance(legacy_proxy, dict):
            raise SettingsError('网络代理配置无效。')
        data['network_proxy'] = {
            'mode': 'manual' if legacy_proxy.get('enabled') else 'direct',
            'url': legacy_proxy.get('url', ''),
        }
    return data


def validate_app_config(data: dict[str, Any]) -> AppSettings:
    try:
        return AppSettings.model_validate(data).resolve_relative_paths()
    except ValidationError as error:
        if any(item['loc'][0:1] == ('network_proxy',) for item in error.errors(include_input=False)):
            raise SettingsError('网络代理配置无效。手动模式需要无凭据的 HTTP(S) 代理地址。') from None
        raise SettingsError("应用配置无效，请检查路径或请求调度参数的类型与范围。") from None


def load_settings(
    config_dir: Path = Path("config"),
    config_path: Optional[Path] = None,
) -> AppSettings:
    """加载设置，缺失时原子创建默认配置。"""

    path = config_path or config_dir / "app.yaml"
    if not path.exists():
        try:
            with file_write_lock(path):
                if not path.exists():
                    atomic_write_yaml(path, {**DEFAULT_APP_CONFIG, 'config_dir': str(config_dir)})
        except OSError:
            raise SettingsIOError("无法创建应用配置，请检查权限与磁盘空间。") from None
    data = read_app_config(path)
    data.setdefault('config_dir', str(config_dir))
    return validate_app_config(data)
