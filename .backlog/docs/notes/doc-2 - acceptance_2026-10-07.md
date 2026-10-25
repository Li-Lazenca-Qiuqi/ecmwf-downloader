---
id: doc-2
title: acceptance_2026-10-07
type: guide
created_date: '2026-10-25T08:19:00Z'
updated_date: '2026-10-25T08:19:00Z'
---
<!-- source: doc/note/acceptance_2026-10-07.md -->

# 0.5.0 验收记录

日期：2026-10-07。范围见 [PRD](<../../drafts/draft-1 - PRD-0.5.0_acceptance.md>)，原清单已迁入 Backlog，实施说明由 TASK-1 维护；旧清单及重复迁移文件已按用户要求删除。核对基线为 `5f25c98`；当轮保留工作区改动，没有 Git 提交、版本更新或发布。

2026-10-23 注：以下是历史实现与技术验证记录，不代表用户验收，不代表本日重新运行。先前已检查的 7 项迁入「待验收」；真实下载仍无通过证据，当前账号状态未重新探测。

## 变更与隔离

补齐项目文档，修复 `POST /api/v1/accounts` 将公开 DTO 的 `id` 错传给仅接受 `account_id` 的应用服务而产生的 500。新增参数化回归覆盖省略 ID 自动生成 UUID、显式 ID 保留、新增及列表响应不泄露 key，并检查虚构 key 在测试 SecretStore 中实际保存。

验证在 Linux/WSL 内使用 Linux 工具链，Python 3.13.9、Node 22.17.0、npm 10.9.2。配置、数据库、虚构账号、下载目录、构建包与浏览器会话放入独立临时工作区。没有修改原有任务、下载文件、账号配置或凭据。前端构建重定向到临时目录，其产物与 wheel 内发布静态资源逐字节一致。

## 自动验证结果

| 检查 | 实际结果 | 证据边界 |
| --- | --- | --- |
| 全套 pytest | 299 passed；1 条 Starlette/httpx 弃用警告 | 包含旧架构测试，不能解释为新流程全面覆盖 |
| 新增账号 API 回归 | API 测试 5 passed；新架构共 14 个用例 | 使用虚构 key 与临时配置 |
| TypeScript + Vite | 生产构建成功 | 前端运行行为另做浏览器验证 |
| Python 分发 | sdist、wheel 构建成功；最终修复代码重新打包 | 未发布，不更新版本 |
| 独立 wheel 安装 | 缓存依赖离线安装，非 editable 安装 | 未依赖源码路径 |
| 无 Node 运行 | 子进程 PATH 仅安装环境 bin；确认无法发现 node；CLI help/version 和 Web 成功 | 构建时仍需要 Node |
| Web/SPA | 根页面和 tasks、requests/new、accounts、activity、settings 共 6 路由返回 SPA | 不是每个控件的功能验证 |
| 静态资源 | HTML 中 JS/CSS 返回 200，字节与本轮 Vite 产物一致 | wheel 自带预构建资源 |
| Worker 启动 | 安装环境 Web 默认 Worker 的 health 返回 scheduler_running=true | 无真实账号，不消费外部下载 |
| 本地 HTTP 任务 | 小请求预览 1 项；pending → queued → cancelled；无输出文件 | 验证任务控制，不是 CDS 远端请求成功 |
| HTTP SSE | 收到事件 ID；带 Last-Event-ID 重连收到更大的 ID | 覆盖本地事件恢复，不覆盖跨进程崩溃 |
| 安装环境账号 API | 新增虚构账号成功、禁用成功、公开响应不含 key | 不验证真实 CDS 凭据 |
| 文档及差异 | 8 个 Markdown 文件、8 个本地链接、YAML 请求与 `git diff --check` 均通过 | 含 AGENTS 和 7 个文档；另有 1 个 YAML 请求 |

关键命令如下；`QA_ROOT` 指独立临时目录，不能指向生产数据目录：

```bash
uv run --no-sync pytest -o addopts= -p no:cacheprovider -q
cd frontend
npm run build -- --outDir "$QA_ROOT/static"
cd ..
uv build --out-dir "$QA_ROOT/dist"
uv venv "$QA_ROOT/venv" --python .venv/bin/python
uv pip install --python "$QA_ROOT/venv/bin/python" --offline \
  "$QA_ROOT/dist/ecmwf_downloader-0.5.0-py3-none-any.whl"
```

安装验证使用新进程、独立 cwd、绝对配置与数据库路径，移除 PYTHONPATH，并缩小 PATH 后启动已安装 `ecmwf web`。通过真实 HTTP 检查 health、HTML、资源、任务和 SSE；结束后正常关闭进程。账号修复后重新构建安装并重跑上述 HTTP 验证。

## 浏览器验收

Browser plugin not available。用户明确允许临时 Playwright 自动化，使用 Playwright CLI 和现有 Chromium，以 `http://127.0.0.1` 上的独立源码服务验收。服务使用 `--no-worker`，虚构账号仅用于保存流程；Schema 流程前将虚构账号禁用，使用离线回退。

目标流程：概览加载 → 账号池新增虚构账号 → 创建请求及预览 → 创建并入队 → 任务列表出现 queued → 行内取消后显示 cancelled。全程没有真实 CDS 下载。

| 检查 | 结果 |
| --- | --- |
| 页面身份 | URL 与路由一致，标题 ECMWF Downloader |
| 非空与框架错误 | 页面有实际内容；无框架错误覆盖层 |
| 控制台 | 本轮流程无 error/warning；Chromium 有 password input 不在 form 内的 verbose 提示 |
| 桌面 1440 × 1000 | 已截图检查任务状态，主要流程可操作 |
| 截图证据 | desktop-overview、desktop-request-preview、desktop-cancelled、mobile-tasks、mobile-tasks-collapsed |
| 交互 | 新增账号后列表计数变为 1；创建后跳转 tasks 显示排队中；取消后显示已取消 |
| 窄屏 390 × 844 | 未通过完整布局验收：默认导航遮挡；收起后顶部按钮和工具栏仍溢出 |

发现的旧功能缺口：

1. “仅创建任务”调用 `/requests/preview`，页面只增加预览，未创建任务；已在代码与浏览器复现。
2. 离线字段无法编辑 area，单值输入会变为 scalar；浏览器生成请求不等于下述经过选择的完整真实下载请求。
3. 多个按钮未接线；固定服务/调度器/健康状态与实际 API 状态可能不一致；详细清单见 PRODUCT 和 Backlog。

截图保存为本次会话附件，放在项目目录之外；不把截图、浏览器快照或临时脚本加入仓库。整体结论为基本桌面流程通过，管理台功能与窄屏验收仍有缺口。

## 真实 CDS 下载：外部阻塞

用户已选择小请求：[cds_smoke_request.yaml](../../../doc/note/cds_smoke_request.yaml)。数据集为 `reanalysis-era5-single-levels`，2m temperature，2024-01-01 00:00 UTC，North/West/South/East = 31/120/30/121 degree，NetCDF、不压缩、不拆分。该文件仅是 request_payload。

本轮只检查原有配置的账号数量及文件权限，未输出账号、URL 或密钥。新配置 `secrets.yaml` 与旧 `accounts.yaml` 的账号数量都为 0。未向 CDS 提交下载，没有真实 NetCDF 可供检查，不能标记 completed 或科学内容通过。用户需在本地录入账号并确认该数据集访问条件。

本地隐藏输入录入：

```bash
uv run ecmwf account add "your-account-email"
```

后续验收要通过项目 Worker 执行这份请求，使用独立的验收配置、数据库和输出目录，保持原账号及任务完整；不把 key 放入命令行、日志或文档。成功后核对任务 completed、文件大小、`.part` 消失，以及 NetCDF variable、UTC 时间、经纬度范围、单位和缺失值。真实下载的输出属于交付数据，应保留，不能作为临时文件直接清理。

## 后续优先事项

调度器关停及租约转移、遗留任务恢复窗口、同路径并发、设置校验后保存、异常脱敏是可靠性优先项。文件格式、Schema 回退、真实状态展示与界面控件完整性排入后续阶段。具体入口和通过标准现保存在 Backlog；当轮未扩展实施这些修复。
