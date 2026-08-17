# ECMWF Downloader

## 项目背景

本项目是一个本机单用户 ECMWF/CDS 气象数据下载管理工具。当前主线版本为 **0.5.0**，运行环境为 Linux + Python 3.11+。

## 目录结构

```text
ecmwf-downloader/
├── config/                         # app.yaml（非敏感）和 secrets.yaml（凭据）
├── data/                           # SQLite 与下载输出
├── frontend/                       # React + TypeScript + Vite 源码
├── migrations/                     # Alembic 初始迁移
├── src/ecmwf_downloader/
│   ├── domain/                     # 领域模型与状态机
│   ├── application/                # 用例、请求构建、Worker、组合根
│   ├── infrastructure/             # SQLite、Repository、CDS、SecretStore
│   ├── interfaces/cli/             # Typer CLI
│   ├── interfaces/http/            # FastAPI REST + SSE
│   └── web/static/                 # Vite 构建产物，随 wheel 发布
├── tests/test_new/                 # 新架构测试
├── pyproject.toml
└── README.md
```

## 技术路线

- FastAPI 提供 `/api/v1` REST API 和 `/api/v1/events` SSE；Typer 直接调用应用服务，不依赖 Web。
- React/Vite 管理台由 `ecmwf web` 同源托管，默认只绑定 `127.0.0.1`。
- SQLAlchemy + SQLite WAL 保存任务、事件、调度租约、账号运行状态和模板；同一工作区只允许一个调度器租约持有者消费队列。
- Worker 接收通用 `dataset_id + request_payload`，写 `.part` 后原子重命名；默认不覆盖已有目标。
- 任务状态固定为 `pending → queued → running → completed/failed/retry_wait/cancelling/cancelled`，状态变化必须经 Repository 事务并写事件。
- 凭据只放在权限为 `0600` 的 `config/secrets.yaml`，通过 Linux 文件锁、临时文件和原子替换更新；不要在日志、DTO 或 CLI 输出密钥。

## 运行与验证

```bash
uv sync --extra dev
uv run pytest
cd frontend && npm install && npm run build
```

源码和 wheel 都应支持：

```bash
ecmwf --help
ecmwf web
```

不要重新引入 Textual、`src/ui/`、固定 ERA5 字段假设、旧 JSON 任务迁移、暂停/可靠断点续传或非回环 Web 监听，除非需求明确改变。

## 数据迁移策略

0.5.0 使用全新数据库，不导入旧 YAML/JSON 任务历史，也不自动删除旧文件；已有下载文件保留在磁盘但不作为历史任务导入。

最后更新：2026-08-17。
