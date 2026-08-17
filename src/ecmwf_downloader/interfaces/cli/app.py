"""Scriptable CLI that calls application services directly."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable, Optional

import typer
import uvicorn
import yaml

from ecmwf_downloader import __version__
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import DownloadScheduler
from ecmwf_downloader.config import load_settings
from ecmwf_downloader.domain.models import AccountStatus, SplitStrategy, TaskStatus
from ecmwf_downloader.interfaces.http.app import create_app

app = typer.Typer(help="ECMWF Downloader CLI", invoke_without_command=True)
task_app = typer.Typer(help="任务管理", no_args_is_help=True)
dataset_app = typer.Typer(help="数据集与 Schema", no_args_is_help=True)
request_app = typer.Typer(help="请求预览与 AI 建议", no_args_is_help=True)
account_app = typer.Typer(help="账号池管理", no_args_is_help=True)
template_app = typer.Typer(help="请求模板管理", no_args_is_help=True)
config_app = typer.Typer(help="应用配置", no_args_is_help=True)
app.add_typer(task_app, name="task")
app.add_typer(dataset_app, name="dataset")
app.add_typer(request_app, name="request")
app.add_typer(account_app, name="account")
app.add_typer(template_app, name="template")
app.add_typer(config_app, name="config")


def _json(value: Any) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _rows(items: list[dict[str, Any]], columns: list[str]) -> None:
    if not items:
        typer.echo("无数据")
        return
    widths = {column: max(len(column), *(len(str(item.get(column, ""))) for item in items)) for column in columns}
    typer.echo("  ".join(column.ljust(widths[column]) for column in columns))
    typer.echo("  ".join("-" * widths[column] for column in columns))
    for item in items:
        typer.echo("  ".join(str(item.get(column, "")).ljust(widths[column]) for column in columns))


def _ctx_container(ctx: typer.Context) -> AppContainer:
    if ctx.obj is None:
        ctx.obj = AppContainer()
    return ctx.obj


@app.callback()
def main(
    ctx: typer.Context,
    config_dir: Path = typer.Option(Path("config"), "--config-dir", help="配置目录"),
    database: Optional[Path] = typer.Option(None, "--database", help="覆盖 SQLite 路径"),
    version: bool = typer.Option(False, "--version", is_flag=True, help="显示版本"),
):
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    settings = load_settings(config_dir)
    if database:
        settings.database_path = database
    ctx.obj = AppContainer(settings)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def web(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", help="监听地址；首版建议保持本机回环地址"),
    port: int = typer.Option(8000, min=1, max=65535),
    no_worker: bool = typer.Option(False, "--no-worker", help="只启动 API，不启动下载调度器"),
    reload: bool = typer.Option(False, help="开发模式热重载"),
):
    """启动本地 Web 管理台和 FastAPI。"""
    container = _ctx_container(ctx)
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise typer.BadParameter("首版 Web 只允许监听本机回环地址")
    uvicorn.run(create_app(container, with_worker=not no_worker), host=host, port=port, reload=reload)


@app.command()
def worker(ctx: typer.Context):
    """启动独立队列 Worker，直到收到 Ctrl+C。"""
    container = _ctx_container(ctx)
    scheduler = DownloadScheduler(container)
    if not scheduler.start():
        raise typer.Exit(code=3)
    typer.echo("Worker 已启动，按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


@dataset_app.command("list")
def dataset_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")):
    items = _ctx_container(ctx).datasets.list()
    _json(items) if as_json else _rows(items, ["id", "title", "source"])


@dataset_app.command("schema")
def dataset_schema(ctx: typer.Context, dataset_id: str, as_json: bool = typer.Option(False, "--json")):
    container = _ctx_container(ctx)
    schema = container.datasets.schema(dataset_id, container.accounts.next_available())
    _json(schema) if as_json else _json(schema)


def _load_payload(request_file: Optional[Path], values: Iterable[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if request_file:
        with request_file.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise typer.BadParameter("请求文件必须是对象")
        payload.update(loaded)
    for item in values:
        if "=" not in item:
            raise typer.BadParameter(f"--set 必须使用 key=value: {item}")
        key, raw = item.split("=", 1)
        value = yaml.safe_load(raw)
        target = payload
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return payload


@request_app.command("preview")
def request_preview(
    ctx: typer.Context,
    dataset_id: str = typer.Option(..., "--dataset"),
    request_file: Optional[Path] = typer.Option(None, "--request-file"),
    set_values: list[str] = typer.Option([], "--set"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    split: SplitStrategy = typer.Option(SplitStrategy.NONE, "--split"),
):
    container = _ctx_container(ctx)
    _json(container.tasks.preview(dataset_id=dataset_id, request_payload=_load_payload(request_file, set_values), output_dir=output_dir, split_strategy=split))


@request_app.command("suggest")
def request_suggest(
    ctx: typer.Context,
    dataset_id: str = typer.Option(..., "--dataset"),
    prompt: str = typer.Option(..., "--prompt"),
):
    container = _ctx_container(ctx)
    schema = container.datasets.schema(dataset_id, container.accounts.next_available())
    _json(container.ai.suggest(schema, prompt))


@task_app.command("create")
def task_create(
    ctx: typer.Context,
    dataset_id: str = typer.Option(..., "--dataset"),
    request_file: Optional[Path] = typer.Option(None, "--request-file"),
    set_values: list[str] = typer.Option([], "--set"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    split: SplitStrategy = typer.Option(SplitStrategy.NONE, "--split"),
    filename: Optional[str] = typer.Option(None),
    enqueue: bool = typer.Option(False, "--enqueue"),
    overwrite: Optional[bool] = typer.Option(None, "--overwrite/--no-overwrite"),
    as_json: bool = typer.Option(False, "--json"),
):
    container = _ctx_container(ctx)
    tasks = container.tasks.create(
        dataset_id=dataset_id,
        request_payload=_load_payload(request_file, set_values),
        output_dir=output_dir,
        split_strategy=split,
        filename=filename,
        enqueue=enqueue,
        overwrite=overwrite,
    )
    values = [task.model_dump(mode="json") for task in tasks]
    _json(values) if as_json else _rows(values, ["id", "dataset_id", "status", "filename"])


@task_app.command("list")
def task_list(
    ctx: typer.Context,
    status: Optional[TaskStatus] = typer.Option(None),
    search: Optional[str] = typer.Option(None),
    limit: int = typer.Option(50, min=1, max=500),
    as_json: bool = typer.Option(False, "--json"),
):
    tasks, total = _ctx_container(ctx).tasks.list(status=status, search=search, limit=limit)
    values = [task.model_dump(mode="json") for task in tasks]
    if as_json:
        _json({"items": values, "total": total})
    else:
        _rows(values, ["id", "dataset_id", "status", "progress", "filename"])
        typer.echo(f"共 {total} 个任务")


@task_app.command("show")
def task_show(ctx: typer.Context, task_id: str, as_json: bool = typer.Option(False, "--json")):
    task = _ctx_container(ctx).tasks.get(task_id)
    if task is None:
        raise typer.Exit(code=4)
    _json(task.model_dump(mode="json"))


@task_app.command("enqueue")
def task_enqueue(ctx: typer.Context, task_id: str):
    typer.echo(_ctx_container(ctx).tasks.enqueue(task_id).id)


@task_app.command("cancel")
def task_cancel(ctx: typer.Context, task_id: str):
    typer.echo(_ctx_container(ctx).tasks.cancel(task_id).status.value)


@task_app.command("retry")
def task_retry(ctx: typer.Context, task_id: str):
    typer.echo(_ctx_container(ctx).tasks.retry(task_id).status.value)


@task_app.command("delete")
def task_delete(ctx: typer.Context, task_id: str):
    if not _ctx_container(ctx).tasks.delete(task_id):
        raise typer.Exit(code=4)
    typer.echo("已删除")


@task_app.command("run")
def task_run(ctx: typer.Context, task_id: str, wait: bool = typer.Option(False, "--wait")):
    container = _ctx_container(ctx)
    container.tasks.enqueue(task_id)
    scheduler = DownloadScheduler(container)
    owns_scheduler = scheduler.start()
    if not wait:
        typer.echo("已入队")
        if owns_scheduler:
            scheduler.stop()
        return
    try:
        while True:
            task = container.tasks.get(task_id)
            if task is None:
                raise typer.Exit(code=4)
            if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                typer.echo(task.status.value)
                raise typer.Exit(code=0 if task.status == TaskStatus.COMPLETED else 2)
            time.sleep(0.5)
    finally:
        if owns_scheduler:
            scheduler.stop()


@task_app.command("watch")
def task_watch(
    ctx: typer.Context,
    task_id: str,
    interval: float = typer.Option(0.5, min=0.1, max=30, help="轮询间隔（秒）"),
    as_json: bool = typer.Option(False, "--json"),
):
    """持续观察任务状态，直到任务进入终态。"""
    container = _ctx_container(ctx)
    previous: tuple[Any, ...] | None = None
    terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
    while True:
        task = container.tasks.get(task_id)
        if task is None:
            raise typer.Exit(code=4)
        snapshot = (task.status, task.progress, task.downloaded_bytes, task.error_message)
        if snapshot != previous:
            value = task.model_dump(mode="json")
            _json(value) if as_json else typer.echo(
                f"{task.id}  {task.status.value}  "
                f"{'' if task.progress is None else f'{task.progress:.1f}%'}"
            )
            previous = snapshot
        if task.status in terminal:
            raise typer.Exit(code=0 if task.status == TaskStatus.COMPLETED else 2)
        time.sleep(interval)


@account_app.command("list")
def account_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")):
    values = [item.model_dump(mode="json") for item in _ctx_container(ctx).accounts.list()]
    _json(values) if as_json else _rows(values, ["id", "email", "status", "used_count", "fail_count"])


@account_app.command("add")
def account_add(
    ctx: typer.Context,
    email: str,
    key: str = typer.Option(..., prompt=True, hide_input=True),
    url: str = typer.Option("https://cds.climate.copernicus.eu/api"),
):
    item = _ctx_container(ctx).accounts.add(email=email, key=key, url=url)
    typer.echo(item.id)


@account_app.command("edit")
def account_edit(
    ctx: typer.Context,
    account_id: str,
    email: Optional[str] = None,
    key: Optional[str] = typer.Option(None, prompt=False, hide_input=True),
    url: Optional[str] = None,
):
    container = _ctx_container(ctx)
    account = container.secrets.get_account(account_id)
    if not account:
        raise typer.Exit(code=4)
    values = {**account, **{key: value for key, value in {"email": email, "key": key, "url": url}.items() if value is not None}}
    container.secrets.upsert_account(values)
    typer.echo("已保存")


@account_app.command("test")
def account_test(ctx: typer.Context, account_id: str):
    ok, message = _ctx_container(ctx).accounts.test(account_id)
    typer.echo(message)
    if not ok:
        raise typer.Exit(code=2)


@account_app.command("enable")
def account_enable(ctx: typer.Context, account_id: str):
    _ctx_container(ctx).accounts.set_status(account_id, AccountStatus.ACTIVE)
    typer.echo("已启用")


@account_app.command("disable")
def account_disable(ctx: typer.Context, account_id: str):
    _ctx_container(ctx).accounts.set_status(account_id, AccountStatus.DISABLED)
    typer.echo("已禁用")


@account_app.command("delete")
def account_delete(ctx: typer.Context, account_id: str):
    if not _ctx_container(ctx).accounts.delete(account_id):
        raise typer.Exit(code=4)
    typer.echo("已删除")


@template_app.command("list")
def template_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")):
    values = _ctx_container(ctx).templates.list()
    _json(values) if as_json else _rows(values, ["id", "name", "updated_at"])


@template_app.command("save")
def template_save(ctx: typer.Context, name: str, request_file: Path):
    _ctx_container(ctx).templates.save(name, _load_payload(request_file, ()))
    typer.echo("已保存")


@template_app.command("show")
def template_show(ctx: typer.Context, template_id: str):
    item = _ctx_container(ctx).templates.get(template_id)
    if not item:
        raise typer.Exit(code=4)
    _json(item)


@template_app.command("delete")
def template_delete(ctx: typer.Context, template_id: str):
    if not _ctx_container(ctx).templates.delete(template_id):
        raise typer.Exit(code=4)
    typer.echo("已删除")


@config_app.command("show")
def config_show(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")):
    values = _ctx_container(ctx).settings.model_dump(mode="json")
    _json(values)


@config_app.command("set")
def config_set(ctx: typer.Context, key: str, value: str):
    container = _ctx_container(ctx)
    allowed = {
        "download.output_dir",
        "download.max_workers",
        "download.max_retries",
        "download.retry_delays",
        "download.poll_interval",
        "download.overwrite",
        "ai.enabled",
        "ai.base_url",
        "ai.model",
        "ai.temperature",
        "ai.timeout",
    }
    if key not in allowed:
        raise typer.BadParameter(f"仅支持: {', '.join(sorted(allowed))}")
    section, field = key.split(".", 1)
    container.update_settings({section: {field: yaml.safe_load(value)}})
    typer.echo("已更新")


@config_app.command("set-ai-key")
def config_set_ai_key(ctx: typer.Context, key: str = typer.Option(..., prompt=True, hide_input=True)):
    """将 AI API Key 写入独立的 secrets.yaml。"""
    _ctx_container(ctx).secrets.update_ai({"api_key": key})
    typer.echo("AI Key 已安全保存")
