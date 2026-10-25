# ECMWF Downloader

## 项目背景

本项目是一个本机单用户 ECMWF/CDS 气象数据下载管理工具。当前主线版本为 **0.5.0**，运行环境为 Linux + Python 3.11+。

## 目录结构

```text
ecmwf-downloader/
├── .backlog/                       # 任务、需求、项目文档与里程碑
├── config/                         # app.yaml（非敏感）和 secrets.yaml（凭据）
├── data/                           # SQLite 与下载输出
├── frontend/                       # React + TypeScript + Vite 源码
├── migrations/                     # Alembic 初始迁移
├── doc/                            # 论文、报告、附件与历史资料
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

- `.backlog/docs/product/doc-1 - Product.md`：当前实现、支持范围及已知限制。
- `.backlog/config.yml`：项目看板配置；项目名为 `ecmwf-downloader`，Git 集成启用，自动提交关闭。
- `.backlog/tasks/`：唯一活动任务来源，状态为 `To Do`、`In Progress`、`待验收`、`Done`；外部阻塞写入任务说明和标签。
- `.backlog/milestones/`：阶段规划和任务归属，不承诺尚未确认的日期或版本号。
- `.backlog/drafts/draft-1 - PRD-0.5.0_acceptance.md`：0.5.0 收尾验收范围与通过标准。
- `.backlog/decisions/decision-1 - 0001_local_cli_web.md`：现有架构及迁移边界。
- `.backlog/docs/notes/doc-2 - acceptance_2026-10-07.md`：历史验证证据、真实下载请求与未验证范围，不视为最新实测。
- `TASK-1`：记忆系统与任务看板迁移，实施说明由 Backlog 维护。
- `doc/archive/README.md`：归档目录使用边界；不保留已迁移的旧清单快照。

报告进度前核对 Backlog、相关代码、近期 Git 历史和工作区状态。已有实现、自动测试通过、用户验收通过和真实 CDS 下载通过是不同证据，不能相互替代。所有任务由用户验收，代理最多转为「待验收」，不勾选用户验收项、不代设 Done、不自动归档未验收事项。用户笼统表示“大部分完成”不等于逐项验收。

## Backlog 使用约定

开始工作先检查配置与现有任务，已初始化时不重复运行 `backlog init`，不覆盖配置。任务、草稿、Backlog 文档、决策及里程碑通过 CLI 修改，不直接编辑 `.backlog/` 下的 Markdown；配置列表可按工具要求修改 YAML。

Backlog 的所有操作统一在 WSL 的仓库根目录使用 CLI，不使用 Backlog MCP；执行前核对当前工作目录与 `.backlog/config.yml`。现有 CLI 基线为 Backlog.md 1.55.2；没有项目内 CLI 时可以使用 `npx --yes --package backlog.md@1.55.2 backlog`，已缓存后可改为 `--offline`。

```bash
backlog config get autoCommit
backlog task list --plain
backlog milestone list
```

`LAST_RUN.md`、`TODO.md` 和 `Roadmap` 均已弃用。已迁入 Backlog 的旧文件、跳转入口、历史快照和重复迁移汇总按用户要求删除，不额外备份；后续只维护 Backlog。收尾清理可再生成的中间文件，保留有效需求、决策、验收证据、发布产物和用户数据。新需求先形成 PRD，经用户确认后登记任务；实现前记录任务计划，做定向验证后交由用户验收。

新增桌面化部分按用户新偏好采用 Electron 包装 Web App，先在 Web 开发并测试；当前项目仍为 CLI + Web，本轮没有引入桌面端或改变架构。提交、版本、Tag 与发布继续分别以用户明确要求为授权；CHANGELOG 只在明确更新版本时修改。

最后更新：2026-10-23。

## Backlog 工作流

- 在仓库根目录通过 CLI 操作，先核对 `.backlog/config.yml`；保留 Git、`auto_commit: false` 和 `待验收` 状态。
- Drafts 保存完整需求文档，Documents 保存产品说明和专题笔记，Decisions 保存决策；Tasks 与 Milestones 分别管理执行和阶段规划。
- 需求经用户审查后关联或拆分 Tasks；实现和适用验证后最多转为 `待验收`，验收条件和完成状态由用户决定。
- Backlog 记录通过 CLI 修改，不直接编辑其 Markdown。
- 新项目初始化使用 CLI，并指定 `--agent-instructions none` 保留提示词文件。
- 启动 Dashboard 前检查端口占用；跨 Windows/WSL 时检查两侧。同项目可用服务可复用，否则使用空闲端口及 `--non-interactive`，核实项目和实际地址，保留其他服务进程。
- 原需求的批准范围、任务编号和验证证据保留；历史测试结果不代表当前工作区已重新通过验证。
- 论文、研究报告、图片和附件按项目需要保留在原目录。
