"""FastAPI REST/SSE interface for the local application."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import DownloadScheduler
from ecmwf_downloader.domain.models import AccountStatus, TaskStatus
from ecmwf_downloader.interfaces.http.schemas import (
    AccountCreateBody,
    AccountUpdateBody,
    AISuggestionBody,
    BatchBody,
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
    scheduler = DownloadScheduler(app_container) if with_worker else None

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
        version="0.5.0",
        lifespan=lifespan,
    )
    app.state.container = app_container
    app.state.scheduler = scheduler

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError):
        return _problem(422, str(exc), "参数或状态无效")

    @app.exception_handler(KeyError)
    async def _key_error(_request: Request, exc: KeyError):
        return _problem(404, str(exc).strip("'"), "资源不存在")

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError):
        return _problem(422, json.dumps(exc.errors(), ensure_ascii=False, default=str), "请求校验失败")

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
        return result

    @app.get("/api/v1/tasks")
    def list_tasks(
        status: Optional[TaskStatus] = None,
        search: Optional[str] = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        tasks, total = app_container.tasks.list(status=status, search=search, limit=limit, offset=offset)
        return {"items": [_task_json(task) for task in tasks], "total": total, "limit": limit, "offset": offset}

    @app.get("/api/v1/tasks/{task_id}")
    def get_task(task_id: str):
        task = app_container.tasks.get(task_id)
        if task is None:
            return _problem(404, f"任务不存在: {task_id}", "资源不存在")
        return _task_json(task)

    @app.post("/api/v1/requests/preview")
    def preview(body: PreviewBody):
        return {"items": app_container.tasks.preview(**body.model_dump())}

    @app.post("/api/v1/tasks")
    def create_task(body: TaskCreateBody):
        tasks = app_container.tasks.create(**body.model_dump())
        return {"items": [_task_json(task) for task in tasks]}

    @app.post("/api/v1/tasks/{task_id}/enqueue")
    def enqueue_task(task_id: str):
        return _task_json(app_container.tasks.enqueue(task_id))

    @app.post("/api/v1/tasks/{task_id}/cancel")
    def cancel_task(task_id: str):
        return _task_json(app_container.tasks.cancel(task_id))

    @app.post("/api/v1/tasks/{task_id}/retry")
    def retry_task(task_id: str):
        return _task_json(app_container.tasks.retry(task_id))

    @app.delete("/api/v1/tasks/{task_id}")
    def delete_task(task_id: str):
        if not app_container.tasks.delete(task_id):
            return _problem(404, f"任务不存在: {task_id}", "资源不存在")
        return {"deleted": True, "id": task_id}

    @app.post("/api/v1/tasks/actions/{action}")
    def batch_action(action: str, body: BatchBody):
        if action == "enqueue":
            count = app_container.tasks.enqueue_many(body.task_ids)
        elif action == "cancel":
            count = sum(_try_action(app_container.tasks.cancel, task_id) for task_id in body.task_ids)
        elif action == "retry":
            count = sum(_try_action(app_container.tasks.retry, task_id) for task_id in body.task_ids)
        elif action == "delete":
            count = sum(_try_action(app_container.tasks.delete, task_id) for task_id in body.task_ids)
        else:
            return _problem(404, f"未知批量操作: {action}", "操作不存在")
        return {"affected": count}

    @app.get("/api/v1/datasets")
    def list_datasets():
        return {"items": app_container.datasets.list()}

    @app.get("/api/v1/datasets/{dataset_id}/schema")
    def dataset_schema(dataset_id: str):
        account = app_container.accounts.next_available()
        return app_container.datasets.schema(dataset_id, account)

    @app.post("/api/v1/datasets/{dataset_id}/constraints")
    def dataset_constraints(dataset_id: str, selection: dict):
        account = app_container.accounts.next_available()
        return {"constraints": app_container.datasets.constraints(dataset_id, selection, account)}

    @app.get("/api/v1/accounts")
    def list_accounts():
        return {"items": [item.model_dump(mode="json") for item in app_container.accounts.list()]}

    @app.post("/api/v1/accounts")
    def add_account(body: AccountCreateBody):
        return app_container.accounts.add(**body.model_dump()).model_dump(mode="json")

    @app.patch("/api/v1/accounts/{account_id}")
    def update_account(account_id: str, body: AccountUpdateBody):
        account = app_container.secrets.get_account(account_id)
        if not account:
            return _problem(404, f"账号不存在: {account_id}", "资源不存在")
        values = body.model_dump(exclude_none=True)
        values = {**account, **values}
        app_container.secrets.upsert_account(values)
        return next(item for item in app_container.accounts.list() if item.id == account_id).model_dump(mode="json")

    @app.post("/api/v1/accounts/{account_id}/test")
    def test_account(account_id: str):
        ok, message = app_container.accounts.test(account_id)
        if not ok:
            app_container.accounts.record_failure(account_id, message)
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
        values = app_container.settings.model_dump(mode="json")
        return {"database_path": values["database_path"], "config_dir": values["config_dir"], "download": values["download"], "ai": {key: value for key, value in values["ai"].items() if key != "api_key"}}

    @app.patch("/api/v1/settings")
    def patch_settings(body: SettingsPatch):
        values = app_container.update_settings(body.values)
        dumped = values.model_dump(mode="json")
        dumped["ai"] = {key: value for key, value in dumped["ai"].items() if key != "api_key"}
        return dumped

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
        return FileResponse(index)

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (static_dir / path).resolve()
        try:
            inside_static = candidate.is_relative_to(static_dir.resolve())
        except AttributeError:  # pragma: no cover - Python 3.10 compatibility guard
            inside_static = str(candidate).startswith(str(static_dir.resolve()))
        return FileResponse(candidate if inside_static and candidate.is_file() else index)
