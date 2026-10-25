# ECMWF Downloader

ECMWF/CDS 气象数据下载管理工具，面向 Windows 和 Linux，以 CLI 为主要入口，兼顾服务器和本地使用。0.5.0 起采用单用户 CLI + Web 架构：Typer CLI 和后台运行的 FastAPI 服务共享 SQLite、配置、账号池和唯一调度器租约；服务通过本地 HTTP 端口提供 API 与管理台，前端构建产物随 Python wheel 发布。

## 能力概览

- 通用 `dataset_id + request_payload` CDS 请求，不把请求限制为固定 ERA5 字段。
- `none`、按年、按月三种拆分策略；缺少拆分字段时在预览阶段报校验错误。
- SQLite WAL、事务化状态机和事件表：新任务直接进入 `queued → running → completed/failed/retry_wait/cancelling/cancelled`；历史 `pending` 记录保留。
- 数据库租约保证同一工作区只有一个 Worker 消费队列；租约过期时恢复遗留任务并清理 `.part` 文件。
- 下载写入 `.part`，成功后原子重命名；目标文件默认冲突，只有显式 `--overwrite` 才覆盖。
- 账号和 AI 凭据独立存放在权限为 `0600` 的 `config/secrets.yaml`，API、CLI 和日志不输出完整密钥。
- SSE `/api/v1/events` 将 CLI、Web、Worker 的任务事件同步到管理台。
- 首版支持取消，不提供暂停或可靠断点续传；总大小未知时不伪造百分比。

## 快速开始

需要 Python 3.11+，开发环境使用 uv。当前实现和技术验证覆盖 Linux/WSL；Windows 原生文件锁等兼容尚待补齐，暂不能视为原生 Windows 已通过验收。

```bash
uv sync --extra dev
uv run ecmwf --help
```

源码开发时构建管理台（发布 wheel 已包含 `web/static`）：

```bash
cd frontend
npm install
npm run build
cd ..
```

添加 CDS 账号后启动 Web 管理台：

```bash
uv run ecmwf account add analyst@example.com --key 'your-cds-key'
uv run ecmwf web                 # 127.0.0.1:8000，包含默认 Worker
```

浏览器打开 <http://127.0.0.1:8000>。若只运行独立 Worker：

```bash
uv run ecmwf worker
```

## CLI 示例

```bash
# 数据集与请求预览
uv run ecmwf dataset list
uv run ecmwf request preview --dataset reanalysis-era5-pressure-levels \
  --set variable='[temperature]' --set year='[2024]' --split month

# 创建即入队，由后台 ecmwf worker 或 ecmwf web 自动消费
uv run ecmwf task create \
  --dataset reanalysis-era5-pressure-levels \
  --request-file request.yaml \
  --split month \
  --json
uv run ecmwf task list --json
uv run ecmwf task watch TASK_ID --json
uv run ecmwf task cancel TASK_ID

# 所有查询命令都可以使用 --json；配置和模板也可由 CLI 管理
uv run ecmwf account list --json
uv run ecmwf config show --json
uv run ecmwf config set-ai-key
```

CLI 提交后即可退出；下载需要保持 `ecmwf worker` 或默认带调度器的 `ecmwf web` 在后台运行。有可用账号和并发空位时自动开始，其他任务继续排队，不提供预约下载、暂停或全局停止入口。取消正在执行的任务时，可能需要等待当前 CDS 请求结束。

旧 `--enqueue` 参数仍可接受但已无须填写；旧入队接口和隐藏命令仅用于处理历史 `pending` 记录，不会批量启动历史任务。API 显式传入 `enqueue=false` 返回 422，避免创建与新规则不一致的任务。

Web 管理台统一为任务队列、添加任务、账号、设置四个入口。请求参数可直接粘贴为 JSON；输出目录、日期拆分和可选 AI 建议折叠显示，提交前可做不写入任务的本地预览。

请求文件是任意 YAML/JSON 对象，例如：

```yaml
variable: [temperature, geopotential]
year: [2024]
month: ["01", "02"]
time: ["00:00", "12:00"]
data_format: netcdf
download_format: unarchived
```

## HTTP API

FastAPI 以 `/api/v1` 提供版本化接口：

- `/health`、`/summary`
- `/datasets`、`/datasets/{id}/schema`
- `/requests/preview`、`/ai/suggestions`
- `/tasks` 以及 cancel/retry/delete/batch actions；创建即入队，不支持 `enqueue=false`
- `/accounts`、`/templates`、`/settings`
- `/events` SSE（支持 `Last-Event-ID` 重连）

错误响应使用 `application/problem+json`。服务只需监听 `127.0.0.1`。在服务器上可将后端作为后台进程运行，通过 SSH 端口转发从本地浏览器访问；生产构建的前端与 API 共用这一服务端口。当前不提供直接面向局域网或公网的 Web 访问，也不包含多用户认证。

例如，服务器管理台监听 `127.0.0.1:8000` 时，在本地 Bash 运行：

```bash
ssh \
  -N \
  -L 127.0.0.1:18000:127.0.0.1:8000 \
  user@server
```

本地使用 Windows PowerShell 时，对应命令为：

```powershell
ssh `
  -N `
  -L 127.0.0.1:18000:127.0.0.1:8000 `
  user@server
```

随后在本地浏览器打开 <http://127.0.0.1:18000>。`user@server` 替换为实际 SSH 登录目标；隧道保持运行期间可访问管理台。

## 配置和数据

- `config/app.yaml`：非敏感下载、并发、重试和 AI 开关。
- `config/secrets.yaml`：CDS/AI 凭据，自动以 `0600` 权限创建并通过锁文件和原子替换更新。
- `config/app.yaml.example`、`config/secrets.yaml.example`：可提交的结构示例，不包含真实密钥。
- `data/ecmwf.sqlite3`：任务、事件、租约、账号运行状态和模板。
- `data/downloads/`：下载目标及临时 `.part` 文件。

新版本使用全新的 SQLite 数据库，不迁移旧 YAML/JSON 任务历史，也不会自动删除旧文件；磁盘上已有的下载文件会保留但不会被导入为历史任务。

## 开发和测试

```bash
uv run pytest
uv build
```

前端验证：

```bash
cd frontend
npm run build
```

发布前应验证 wheel 在无 Node 环境下可执行 `ecmwf --help`，并由 `ecmwf web` 返回完整 SPA。

## 架构

```text
src/ecmwf_downloader/
├── domain/                 # 状态、DTO 和不依赖框架的规则
├── application/            # 请求、任务、账号、数据集和 Worker 用例
├── infrastructure/         # SQLAlchemy/SQLite、CDS、密钥文件
├── interfaces/cli/         # Typer 命令
├── interfaces/http/        # FastAPI REST + SSE
└── web/static/             # Vite 构建产物（随 wheel 发布）
```

## 官方资源

- [ECMWF Climate Data Store](https://cds.climate.copernicus.eu/)
- [CDS API 使用指南](https://cds.climate.copernicus.eu/api-how-to)
- [cdsapi](https://pypi.org/project/cdsapi/)
