# ECMWF Downloader

## 项目背景

本项目是一个本机单用户 ECMWF/CDS 气象数据下载管理工具。当前主线版本为 **0.5.0**，运行环境为 Linux + Python 3.11+。

## 目录结构

```text
ecmwf-downloader/
├── .backlog/                       # 配置、任务看板与里程碑
├── config/                         # app.yaml（非敏感）和 secrets.yaml（凭据）
├── data/                           # SQLite 与下载输出
├── frontend/                       # React + TypeScript + Vite 源码
├── migrations/                     # Alembic 初始迁移
├── doc/                            # 产品、需求、决策、有效笔记与历史记录
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

以下是完整开发检查命令，不是每次修改都要执行的固定清单。按当前改动只做相关功能验证；文档和看板迁移只检查配置、任务结构、链接和差异，不重跑全量测试，不主动启动视觉验证。

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

## 文档入口与进度依据

- `doc/PRODUCT.md`：当前实现、支持范围及已知限制。
- `.backlog/config.yml`：项目看板配置；项目名为 `ecmwf-downloader`，Git 集成启用，自动提交关闭。
- `.backlog/tasks/`：唯一活动任务来源，状态为 `To Do`、`In Progress`、`待验收`、`Done`；外部阻塞写入任务说明和标签。
- `.backlog/milestones/`：阶段规划和任务归属，不承诺尚未确认的日期或版本号。
- `doc/PRD/0.5.0_acceptance.md`：0.5.0 收尾验收范围与通过标准。
- `doc/decisions/0001_local_cli_web.md`：现有架构及迁移边界。
- `doc/note/acceptance_2026-10-07.md`：历史验证证据、真实下载请求与未验证范围，不视为最新实测。
- `TASK-1`：记忆系统与任务看板迁移，实施说明由 Backlog 维护。
- `doc/archive/README.md`：归档目录使用边界；不保留已迁移的旧清单快照。

报告进度前核对 Backlog、相关代码、近期 Git 历史和工作区状态。已有实现、自动测试通过、用户验收通过和真实 CDS 下载通过是不同证据，不能相互替代。所有任务由用户验收，代理最多转为「待验收」，不勾选用户验收项、不代设 Done、不自动归档未验收事项。用户笼统表示“大部分完成”不等于逐项验收。

## Backlog 使用约定

开始工作先检查配置与现有任务，已初始化时不重复运行 `backlog init`，不覆盖配置。任务、草稿、Backlog 文档、决策及里程碑通过 MCP 或 CLI 修改，不直接编辑 `.backlog/` 下的 Markdown；配置列表可按工具要求修改 YAML。

优先使用 MCP，但必须先确认它属于当前项目。2026-10-23 的会话 MCP 指向其他测试项目，因此本轮使用 WSL 中的 Backlog.md 1.55.2 CLI；后续每次重新核对，不将本轮路由当作永久配置。没有项目内 CLI 时可以使用 `npx --yes --package backlog.md@1.55.2 backlog`，已缓存后可改为 `--offline`；不因此改全局 MCP 配置。

```bash
backlog config get autoCommit
backlog task list --plain
backlog milestone list
```

`LAST_RUN.md`、`TODO.md` 和 `Roadmap` 均已弃用。已迁入 Backlog 的旧文件、跳转入口、历史快照和重复迁移汇总按用户要求删除，不额外备份；后续只维护 Backlog。收尾清理可再生成的中间文件，保留有效需求、决策、验收证据、发布产物和用户数据。新需求先形成 PRD，经用户确认后登记任务；实现前记录任务计划，做定向验证后交由用户验收。

新增桌面化部分按用户新偏好采用 Electron 包装 Web App，先在 Web 开发并测试；当前项目仍为 CLI + Web，本轮没有引入桌面端或改变架构。提交、版本、Tag 与发布继续分别以用户明确要求为授权；CHANGELOG 只在明确更新版本时修改。

最后更新：2026-10-23。
