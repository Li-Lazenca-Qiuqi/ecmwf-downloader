# ECMWF Downloader

ECMWF/CDS 气象数据请求与结果链接管理工具，面向 Windows 和 Linux，以 CLI 为主要入口。Typer CLI 与后台 FastAPI 共享 SQLite、账号和单一调度器；同源 Web 管理台通过本地回环端口及 SSH 转发访问。

软件负责提交请求、监视远端处理并返回下载链接；文件传输交给用户的专业下载器，不在本机下载或导出数据。

## 能力概览

- 从官方完整目录选择 CDS 数据集，通过通用字段、AI 或 CLI 编辑并校验科学参数。
- 不拆分、按年、按月和按日拆分请求，预览中检查字段与实际日历。
- 单独提交 CDS 请求并保存远端 ID，监视排队和处理，重启后继续查询同一作业。
- 提交结果不明确时先核实并关联远端 ID，不盲目重复提交；取消等待源站确认。
- 返回真实结果 URL 与可用元数据，支持单条、批量复制、CLI JSON 和手动更新链接。
- NCAR AWS/GDEX 分别列出原文件，返回 HTTPS 链接；不裁剪、不转换或传输文件体。ARCO 本地导出已移除。
- SQLite WAL、事务及调度租约协调并发，账号与 AI 密钥只放在独立 secrets.yaml。
- 结果可能随源站缓存清理而失效；没有本地传输进度、输出目录、覆盖、暂停或预约下载。

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
# 预览已提供的 CDS 小请求
uv run ecmwf dataset list
uv run ecmwf request preview --dataset reanalysis-era5-single-levels \
  --request-file doc/note/cds_smoke_request.yaml --split month

# 创建后由后台 worker 或 web 提交并监视
uv run ecmwf task create --dataset reanalysis-era5-single-levels \
  --request-file doc/note/cds_smoke_request.yaml --json
uv run ecmwf task list --json
uv run ecmwf task watch TASK_ID --json
uv run ecmwf task links TASK_ID --json
uv run ecmwf task links            # 全部就绪链接
uv run ecmwf task refresh TASK_ID   # 更新原作业结果，不新增提交
uv run ecmwf task cancel TASK_ID
uv run ecmwf task attach TASK_ID REMOTE_ID  # 核实并关联不明确提交

uv run ecmwf account list --json
uv run ecmwf config show --json
uv run ecmwf config set requests.poll_interval 5
uv run ecmwf config set-ai-key
```

CLI 创建后可退出；提交与监视需要保持 ecmwf worker 或默认带调度器的 ecmwf web 运行。查询失败的重试继续使用原远端 ID；只有用户明确重新提交已失败、取消或失效的请求，才发起新作业。

Web 管理台有请求队列、提交请求、账号和设置。字段与 AI、手动规模、只读预览和拆分保留，按钮为“提交请求”；不再选择本地输出目录。结果详情提供文件链接，交给下载器自行选择保存位置。

默认来源 CDS，另有 NCAR AWS ERA5、NCAR GDEX ERA5；NCAR 每个已发布文件对应一个链接，无需 CDS 账号，不做区域或日期子集。CLI 可用 --source ncar 或 --source gdex；ARCO 本地子集导出已取消，也不以 Zarr 地址冒充所选子集文件。

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
- /tasks 以及 cancel/retry/delete/batch actions；创建即进入请求队列
- /tasks/{id}/links、/tasks/{id}/refresh、/tasks/{id}/attach
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

- `config/app.yaml`：非敏感 requests 并发、轮询、查询重试和 AI 开关。
- `config/secrets.yaml`：CDS/AI 凭据，自动以 `0600` 权限创建并通过锁文件和原子替换更新。
- `config/app.yaml.example`、`config/secrets.yaml.example`：可提交的结构示例，不包含真实密钥。
- `data/ecmwf.sqlite3`：请求、结果链接元数据、事件、租约、账号运行状态和模板。
- 已有下载文件保持原状，新流程不会创建下载目标或临时数据文件。

新请求使用独立 request_tasks/request_events 表，启动仅创建缺失表。已有 tasks/task_events、账号和下载文件保留，不导入新请求队列、不清空或重建；没有 Alembic 或已有表结构自动升级。requests 配置替代 download 分组，旧输出目录不再参与运行。

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
- [ecmwf-datastores-client](https://ecmwf.github.io/ecmwf-datastores-client/)
