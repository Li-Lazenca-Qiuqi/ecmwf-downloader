"""CDS 远端提交、作业状态和结果元数据；不读取数据文件体。"""
from __future__ import annotations
from typing import Any
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from ecmwf.datastores import Client as DatastoresClient
import requests

from ecmwf_downloader.config import service_url

class ProviderError(RuntimeError):
    pass

class SubmissionRejected(ProviderError):
    pass

class SubmissionUncertain(ProviderError):
    pass

class CDSProvider:
    def __init__(self, account: dict[str, Any]):
        if not account or not account.get("key"):
            raise ProviderError("账号缺少 API Key")
        self.account = account

    def _client(self):
        return DatastoresClient(
            url=service_url(self.account.get("url", "https://cds.climate.copernicus.eu/api")),
            key=self.account["key"], timeout=(10, 20), maximum_tries=1,
            cleanup=False, progress=False, sleep_max=1, retry_after=1,
            log_callback=lambda *args: None,
        )

    def submit(self, dataset_id, payload):
        try:
            remote = self._client().submit(dataset_id, payload)
            return remote.request_id
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            if code is not None and 400 <= code < 500 and code not in {408, 429}:
                raise SubmissionRejected(f"CDS 拒绝提交（HTTP {code}），请检查参数、账号和数据集条款。") from None
            raise SubmissionUncertain("提交响应不明确；请到官方请求页核实并关联远端 ID，不会自动重发。") from None
        except Exception:
            raise SubmissionUncertain("提交响应不明确；请到官方请求页核实并关联远端 ID，不会自动重发。") from None

    def inspect(self, request_id):
        try:
            client = self._client()
            remote = client.get_remote(request_id)
            status = remote.status
            assets = []
            if status == 'successful':
                result = client.get_results(request_id)
                asset = result.asset
                url = result.location
                assets = [{"url": url,
                           "filename": asset.get("title") or PurePosixPath(unquote(urlsplit(url).path)).name or None,
                           "size": asset.get("file:size"), "content_type": asset.get("type"),
                           "expires_at": asset.get("expires_at")}]
            return status, assets
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            if code in {404, 410}:
                return 'expired', []
            raise ProviderError("CDS 状态或结果查询失败，请检查账号权限与网络。") from None
        except Exception:
            raise ProviderError("CDS 状态或结果查询失败，请检查账号权限与网络。") from None

    def cancel(self, request_id):
        try:
            client = self._client()
            receipt = client.get_remote(request_id).delete()
            if receipt.get('status') in {'dismissed', 'deleted', 'cancelled'}:
                return
            if client.get_remote(request_id).status not in {'dismissed', 'deleted', 'cancelled'}:
                raise ProviderError("远端取消尚待确认，将继续查询。")
        except ProviderError:
            raise
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {404, 410}:
                return
            raise ProviderError("尚未确认远端取消，稍后继续查询或重试。") from None
        except Exception:
            raise ProviderError("尚未确认远端取消，稍后继续查询或重试。") from None

    def verify_request(self, request_id, dataset_id, payload):
        try:
            remote = self._client().get_remote(request_id)
            collection_id, request = remote.collection_id, remote.request
        except Exception:
            raise ProviderError("无法核实远端请求 ID，请检查所属账号与官方请求详情。") from None
        if collection_id != dataset_id or request != payload:
            raise ValueError("远端请求的数据集或参数与本地记录不一致")

    def check_connection(self) -> tuple[bool, str]:
        try:
            client = self._client()
            client.check_authentication()
            return True, "账号认证通过；数据集条款和请求权限需在提交时验证。"
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {401, 403}:
                return False, "CDS 认证未通过，请检查 API Key 是否有效。"
            if status == 404:
                return False, "认证接口不存在（HTTP 404），请检查 API 地址。"
            return False, f"CDS 服务返回 HTTP {status}，请稍后重试。" if status else "CDS 服务请求失败，请稍后重试。"
        except requests.exceptions.SSLError:
            return False, "TLS 证书校验失败，请检查网络代理或证书配置。"
        except requests.Timeout:
            return False, "连接 CDS 超时，请检查后台所在机器的网络。"
        except requests.ConnectionError:
            return False, "无法连接 CDS，请检查后台所在机器的网络或代理。"
        except Exception:
            # 第三方异常可能含请求头、URL 或令牌，不直接传给界面。
            return False, "无法完成 CDS 认证检查，请检查 API 地址与客户端配置。"
