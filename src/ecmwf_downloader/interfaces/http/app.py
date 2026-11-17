"""FastAPI REST/SSE interface for the local application."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from ecmwf_downloader import __version__
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import (
    AI_REASONING_EFFORTS, NetworkProxySettings, SettingsIOError, public_ai_settings, service_url,
)
from ecmwf_downloader.infrastructure.secrets import SecretStoreError
from ecmwf_downloader.infrastructure.mirrors import DEFAULT_PREFIX, MIRROR_IDS
from ecmwf_downloader.infrastructure.cds import ProviderError
from ecmwf_downloader.infrastructure.catalogue import check_network
from ecmwf_downloader.application.worker import RequestScheduler
from ecmwf_downloader.domain.models import AccountStatus, TaskStatus, SplitStrategy
from ecmwf_downloader.interfaces.http.schemas import (
    AttachBody,
    AccountCreateBody,
    AccountUpdateBody,
    AISuggestionBody,
    AIConfigBody,
    AIConnectionTestBody,
    BatchBody,
    CostingBody,
    PreviewBody,
    SettingsPatch,
    TaskCreateBody,
    TemplateBody,
)


def _problem(status: int, detail: str, title: str = "请求失败") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": title, "status": status, "detail": detail},
    )


def _task_json(task):
    return task.model_dump(mode="json") if task is not None else None


def create_app(container: Optional[AppContainer] = None, *, with_worker: bool = True) -> FastAPI:
    app_container = container or AppContainer()
    scheduler = RequestScheduler(app_container) if with_worker else None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if scheduler is not None:
            scheduler.start()
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.stop()

    app = FastAPI(
        title="ECMWF Downloader API",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.container = app_container
    app.state.scheduler = scheduler

    @app.exception_handler(ProviderError)
    async def _provider_error(_request: Request, exc: ProviderError):
        return _problem(503, str(exc), "数据源服务暂不可用")

    @app.exception_handler(SettingsIOError)
    @app.exception_handler(SecretStoreError)
    async def _storage_error(_request: Request, exc: SettingsIOError | SecretStoreError):
        return _problem(503, str(exc), "配置存储不可用")

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError):
        return _problem(422, str(exc), "参数或状态无效")

    @app.exception_handler(KeyError)
    async def _key_error(_request: Request, exc: KeyError):
        return _problem(404, str(exc).strip("'"), "资源不存在")

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, _exc: RequestValidationError):
        if _request.url.path.startswith('/api/v1/ai/'):
            return _problem(422, 'AI 参数或配置无效，请检查字段类型、服务地址与模型', '请求校验失败')
        return _problem(422, "请检查必填项、字段类型和取值范围。", "请求校验失败")

    @app.exception_handler(HTTPException)
    async def _http_error(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False, default=str)
        return _problem(exc.status_code, detail, "HTTP 请求失败")

    @app.get("/api/v1/health")
    def health():
        return {
            "status": "ok",
            "scheduler_running": bool(scheduler and scheduler.is_running),
            "active_workers": scheduler.active_count if scheduler else 0,
            "database": str(app_container.settings.database_path),
        }

    @app.get("/api/v1/summary")
    def summary():
        result = app_container.tasks.summary()
        result["scheduler_running"] = bool(scheduler and scheduler.is_running)
        result["active_workers"] = scheduler.active_count if scheduler else 0
        result["max_workers"] = scheduler.max_workers if scheduler else None
        result["available_accounts"] = sum(
            account.status == AccountStatus.ACTIVE for account in app_container.accounts.list()
        )
        return result

    @app.get("/api/v1/tasks")
    def list_tasks(
        status: Optional[TaskStatus] = None,
        search: Optional[str] = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        cursor: Optional[str] = Query(None, max_length=400),
    ):
        if cursor is None:
            tasks, total = app_container.tasks.list(status=status, search=search, limit=limit, offset=offset)
            return {"items": [_task_json(task) for task in tasks], "total": total, "limit": limit, "offset": offset}
        after = None
        if cursor:
            try:
                created, batch_id, position, task_id = json.loads(cursor)
                after = datetime.fromisoformat(created), str(batch_id), int(position), str(task_id)
            except (ValueError, TypeError):
                raise ValueError('队列游标无效，请重新加载') from None
        tasks, total = app_container.tasks.list(status=status, search=search, limit=limit + 1, after=after)
        next_cursor = None
        if len(tasks) > limit:
            tasks = tasks[:limit]
            last = tasks[-1]
            next_cursor = json.dumps([
                last.created_at.isoformat(), last.batch.batch_id if last.batch else '',
                last.batch.position if last.batch else 0, last.id,
            ], separators=(',', ':'))
        return {"items": [_task_json(task) for task in tasks], "total": total, "next_cursor": next_cursor}

    @app.get("/api/v1/request-batches/{batch_id}")
    def request_batch(batch_id: str):
        tasks = app_container.tasks.batch(batch_id)
        if not tasks:
            return _problem(404, "请求批次不存在", "资源不存在")
        return {
            "name": tasks[0].batch.name,
            "total": tasks[0].batch.total,
            "items": [
                {
                    "id": task.id, "position": task.batch.position, "status": task.status,
                    "links": [asset.url for asset in task.results] if task.status == TaskStatus.COMPLETED else [],
                }
                for task in tasks
            ],
        }

    @app.get("/api/v1/tasks/{task_id}")
    def get_task(task_id: str):
        task = app_container.tasks.get(task_id)
        if task is None:
            return _problem(404, f"任务不存在: {task_id}", "资源不存在")
        return _task_json(task)

    @app.post("/api/v1/requests/preview")
    def preview(body: PreviewBody):
        warnings: list[str] = []
        items = app_container.tasks.preview(**body.model_dump(), warnings=warnings)
        return {"items": items, "warnings": warnings}

    @app.post("/api/v1/tasks")
    def create_task(body: TaskCreateBody):
        tasks = app_container.tasks.create(**body.model_dump())
        return {"items": [_task_json(task) for task in tasks]}

    @app.post("/api/v1/tasks/{task_id}/cancel")
    def cancel_task(task_id: str):
        return _task_json(app_container.tasks.cancel(task_id))

    @app.post("/api/v1/tasks/{task_id}/retry")
    def retry_task(task_id: str):
        return _task_json(app_container.tasks.retry(task_id))

    @app.post("/api/v1/tasks/{task_id}/refresh")
    def refresh_task(task_id: str):
        return _task_json(app_container.tasks.refresh(task_id))

    @app.post("/api/v1/tasks/{task_id}/attach")
    def attach_task(task_id: str, body: AttachBody):
        return _task_json(app_container.tasks.attach(task_id, body.remote_request_id))

    @app.get("/api/v1/tasks/{task_id}/links")
    def result_links(task_id: str):
        task = app_container.tasks.get(task_id)
        if task is None:
            return _problem(404, "请求不存在", "资源不存在")
        return {"status": task.status, "items": [item.model_dump(mode="json") for item in task.results]
                if task.status == TaskStatus.COMPLETED else []}

    @app.delete("/api/v1/tasks/{task_id}")
    def delete_task(task_id: str):
        if not app_container.tasks.delete(task_id):
            return _problem(404, f"任务不存在: {task_id}", "资源不存在")
        return {"deleted": True, "id": task_id}

    @app.post("/api/v1/tasks/actions/{action}")
    def batch_action(action: str, body: BatchBody):
        if action == "cancel":
            count = sum(_try_action(app_container.tasks.cancel, task_id) for task_id in body.task_ids)
        elif action == "retry":
            count = sum(_try_action(app_container.tasks.retry, task_id) for task_id in body.task_ids)
        elif action == "delete":
            count = sum(_try_action(app_container.tasks.delete, task_id) for task_id in body.task_ids)
        else:
            return _problem(404, f"未知批量操作: {action}", "操作不存在")
        return {"affected": count}

    @app.get("/api/v1/datasets")
    def list_datasets(q: str = '', refresh: bool = False, source: str = 'cds'):
        return app_container.datasets.list(q, refresh=refresh, source=source)

    @app.get("/api/v1/datasets/{dataset_id}/schema")
    def dataset_schema(dataset_id: str, refresh: bool = False, prefix: str = DEFAULT_PREFIX):
        account = None if dataset_id in MIRROR_IDS else app_container.accounts.next_available()
        return app_container.datasets.schema(dataset_id, account, refresh=refresh, prefix=prefix)

    @app.post("/api/v1/datasets/{dataset_id}/constraints")
    def dataset_constraints(dataset_id: str, selection: dict):
        account = app_container.accounts.next_available()
        return app_container.datasets.constraints(dataset_id, selection, account)

    @app.post("/api/v1/datasets/{dataset_id}/costing")
    def dataset_costing(dataset_id: str, body: CostingBody):
        if body.split_strategy != SplitStrategy.NONE or body.split_count is not None:
            plans = app_container.tasks.plan(dataset_id=dataset_id, **body.model_dump())
            account = app_container.accounts.next_available()
            return app_container.datasets.costing_plan(dataset_id, [plan.payload for plan in plans], account)
        selection = app_container.tasks.prepare_request(dataset_id, body.request_payload,
                                                       body.schema_revision, body.editor_values,
                                                       SplitStrategy.NONE)
        account = None if dataset_id in MIRROR_IDS else app_container.accounts.next_available()
        return app_container.datasets.costing(dataset_id, selection, account)

    @app.get("/api/v1/accounts")
    def list_accounts():
        return {"items": [item.model_dump(mode="json") for item in app_container.accounts.list()]}

    @app.post("/api/v1/accounts")
    def add_account(body: AccountCreateBody):
        return app_container.accounts.add(
            email=body.email,
            key=body.key,
            url=body.url,
            account_id=body.id,
        ).model_dump(mode="json")

    @app.patch("/api/v1/accounts/{account_id}")
    def update_account(account_id: str, body: AccountUpdateBody):
        account = app_container.secrets.get_account(account_id)
        if not account:
            return _problem(404, f"账号不存在: {account_id}", "资源不存在")
        values = body.model_dump(exclude_none=True)
        if 'url' in values:
            values['url'] = service_url(values['url'])
        values = {**account, **values}
        app_container.secrets.upsert_account(values)
        return next(item for item in app_container.accounts.list() if item.id == account_id).model_dump(mode="json")

    @app.post("/api/v1/accounts/{account_id}/test")
    def test_account(account_id: str):
        ok, message = app_container.accounts.test(account_id)
        return {"ok": ok, "message": message}

    @app.post("/api/v1/accounts/{account_id}/{action}")
    def account_action(account_id: str, action: str):
        if action not in {"enable", "disable"}:
            return _problem(404, f"未知账号操作: {action}", "操作不存在")
        status = AccountStatus.ACTIVE if action == "enable" else AccountStatus.DISABLED
        return app_container.accounts.set_status(account_id, status).model_dump(mode="json")

    @app.delete("/api/v1/accounts/{account_id}")
    def delete_account(account_id: str):
        if not app_container.accounts.delete(account_id):
            return _problem(404, f"账号不存在: {account_id}", "资源不存在")
        return {"deleted": True, "id": account_id}

    @app.get('/api/v1/ai/config')
    def ai_configuration():
        return app_container.ai.configuration()

    @app.patch('/api/v1/ai/config')
    def update_ai_configuration(body: AIConfigBody):
        key = body.api_key.get_secret_value().strip() if body.api_key is not None else None
        values = body.model_dump(exclude={'api_key'})
        if 'reasoning_effort' not in body.model_fields_set:
            values.pop('reasoning_effort')
        app_container.update_settings({'ai': values}, ai_key=key)
        return app_container.ai.configuration()

    @app.post("/api/v1/ai/test")
    def test_ai_connection(body: AIConnectionTestBody):
        key = body.api_key.get_secret_value().strip() if body.api_key else ''
        try:
            app_container.ai.test_connection(
                base_url=body.base_url, model=body.model, json_mode=body.json_mode, api_key=key,
                reasoning_effort=body.reasoning_effort, network=body.network_proxy,
            )
        except RuntimeError as exc:
            return _problem(503, str(exc), "AI 服务不可用")
        return {"message": "连接成功，模型已响应。"}

    @app.post("/api/v1/ai/suggestions")
    def ai_suggestion(body: AISuggestionBody):
        try:
            return {"suggestion": app_container.ai.suggest(body.field_schema, body.user_request)}
        except RuntimeError as exc:
            return _problem(503, str(exc), "AI 服务不可用")

    @app.get("/api/v1/templates")
    def list_templates():
        return {"items": app_container.templates.list()}

    @app.post("/api/v1/templates")
    def save_template(body: TemplateBody):
        return app_container.templates.save(body.name, body.payload)

    @app.get("/api/v1/templates/{template_id}")
    def get_template(template_id: str):
        item = app_container.templates.get(template_id)
        return item if item else _problem(404, "模板不存在", "资源不存在")

    @app.delete("/api/v1/templates/{template_id}")
    def delete_template(template_id: str):
        if not app_container.templates.delete(template_id):
            return _problem(404, "模板不存在", "资源不存在")
        return {"deleted": True, "id": template_id}

    @app.get("/api/v1/settings")
    def get_settings():
        settings = app_container.settings.model_dump(mode="json")
        return {**settings, "ai": public_ai_settings(settings["ai"]), "ai_config": app_container.ai.configuration(),
                "ai_reasoning_efforts": AI_REASONING_EFFORTS}

    @app.get("/api/v1/settings/ai-key", include_in_schema=False)
    def settings_ai_key(request: Request):
        loopback_hosts = {"127.0.0.1", "localhost", "::1"}
        if (request.url.hostname not in loopback_hosts or not request.client
                or request.client.host not in loopback_hosts or request.headers.get("sec-fetch-site") != "same-origin"):
            return _problem(403, "请从本机管理台的设置页读取 API Key。", "禁止访问")
        key = app_container.secrets.ai_config().get("api_key") or ""
        return JSONResponse({"api_key": key}, headers={"Cache-Control": "no-store"})

    @app.patch("/api/v1/settings")
    def patch_settings(body: SettingsPatch):
        key = body.ai_api_key.get_secret_value().strip() if body.ai_api_key is not None else None
        app_container.update_settings(body.values, ai_key=key)
        return get_settings()

    @app.post("/api/v1/settings/network-proxy/test")
    def test_network_proxy(body: NetworkProxySettings):
        ok, message = check_network(body)
        return {"ok": ok, "message": message}

    @app.get("/api/v1/events")
    async def events(request: Request, last_event_id: int = Query(0, alias="last_event_id"), header_event_id: Optional[str] = Header(None, alias="Last-Event-ID")):
        async def stream() -> AsyncIterator[str]:
            try:
                cursor = int(header_event_id or last_event_id or 0)
            except (TypeError, ValueError):
                cursor = 0
            while True:
                if await request.is_disconnected():
                    break
                items = app_container.tasks_repository.events_after(cursor)
                if items:
                    for item in items:
                        cursor = item["id"]
                        yield f"id: {cursor}\nevent: {item['event_type']}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    _mount_static(app)
    return app


def _try_action(callback, task_id: str) -> int:
    try:
        callback(task_id)
        return 1
    except (KeyError, ValueError):
        return 0


def _mount_static(app: FastAPI) -> None:
    static_dir = Path(__file__).resolve().parents[2] / "web" / "static"
    index = static_dir / "index.html"
    if not index.exists():
        return

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API 不存在")
        candidate = (static_dir / path).resolve()
        try:
            inside_static = candidate.is_relative_to(static_dir.resolve())
        except AttributeError:  # pragma: no cover - Python 3.10 compatibility guard
            inside_static = str(candidate).startswith(str(static_dir.resolve()))
        if inside_static and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
