# ECMWF Downloader

## 项目背景

面向 Windows/Linux 的单用户 ECMWF/CDS 请求与结果链接管理工具，以 CLI 为主要入口，FastAPI 后台同源提供 React/Vite 管理台和 API。Linux 服务器经 SSH 端口转发访问，服务只需回环监听。版本仍为 0.5.0，Python 3.11+；本轮未更新版本。Linux/WSL 已验证，Windows 原生文件锁、权限及后台运行仍待验收。

用户已批准 DRAFT-7，实施见 TASK-32：软件只提交请求、监视远端状态并返回结果链接，科学数据传输交给专业下载器。不得重新引入本地下载、ARCO NetCDF 导出、输出目录浏览、覆盖或传输进度，除非用户明确改变需求。

## 目录地图

- .backlog/：唯一活动任务、PRD、产品、决策及验收证据，仅 CLI 修改。
- config/：非敏感 app.yaml 与独立 secrets.yaml，不得输出凭据。
- data/：SQLite 和既有用户文件；新流程不创建下载文件。
- frontend/：React + TypeScript + Vite。
- src/ecmwf_downloader/domain/：字段、状态、请求与结果资产模型。
- application/：请求编译/拆分、账号/模板及提交监视调度器。
- infrastructure/：SQLite、仓库、CDS 控制/结果元数据与 NCAR 目录/链接。
- interfaces/cli/、interfaces/http/：Typer、FastAPI REST/SSE。
- web/static/：随 wheel 发布的生产前端；tests/test_new/ 为当前架构测试。
- doc/：研究资料和有效附件；README 对外说明，不承载内部进度。

## 技术路线

- CLI 直接调用应用服务；ecmwf web 通过 127.0.0.1 提供 Web、/api/v1、SSE。不引入非回环监听、多用户认证或本轮未要求的 Electron。
- domain/schema.py、application/request_compiler.py 保存真实字段、分组、能力和指纹；Web 用 schema_revision + editor_values + request_payload 绑定预览/创建，CLI compile/schema-check 复用。字段分类完整不等于全部远端组合已验收。
- network_proxy 为后端出站请求选择直连、系统代理或手动 HTTP(S) 代理，覆盖 CDS、NCAR 和 AI。设置页统一保存，网络测试通过 CDS 公开目录。旧 cds_proxy 配置在加载时迁移。
- 官方 CDS 目录完整分页、缓存一小时，按名称/ID 搜索，无账号可查目录；字段、约束、costing、提交需要可用账号，不静默回退为固定 ERA5 字段。
- 默认 CDS，ecmwf-datastores-client 独立 submit/get_remote/get_results，显式 cleanup=False，不调用 retrieve/download，不读取科学数据文件体，也不自动删除已就绪远端作业。
- 镜像为 mirror-ncar-era5、mirror-ncar-gdex-era5，分别列目录并用 HEAD 读取文件响应头、返回 HTTPS 链接；一个原文件一个任务，不裁剪或日期拆分，不需要或修改 CDS 账号统计。
- mirror-arco-era5 已移除，不提供本地 Zarr/NetCDF 导出或伪造远端子集链接。相关可选依赖和 cdsapi 已移除。
- 新 request_tasks/request_events 保存编译请求、绑定账号、远端 ID/状态与资产列表；原 tasks/task_events 保留但不导入新队列，不清空、删除或重建用户数据库及文件。
- request_batch_items 独立保存提交名称、批次 ID、计划序号和原总份数，与新请求一并入库。旧请求无批次记录时沿用原标题。
- request_submission_accounts 与批次同事务保存每份请求指定的 CDS 账号。指定账号暂不可用时该份继续排队，旧请求沿用自动分配。
- SQLAlchemy create_all 只建缺失表，无 Alembic、自动 ALTER TABLE 或数据库重建；后续新字段须单独确认。
- 单一队列自动提交，状态 queued/submitting/accepted/running/refreshing/completed/failed/cancelling/cancelled/expired/submission_unknown；completed 仅表示链接就绪，没有远端百分比就只显示状态。
- 成功提交立即保存远端 ID 和账号；重启按 ID 继续查询。查询退避重试不重新提交；不明确 POST/中断进入待核实，核对后关联 ID，禁止盲目重发。
- 取消与就绪共用写事务，远端确认前保持取消中；DELETE 受理信息不等于已取消。监视失败但作业可能运行时，先取消或恢复监视才能删记录。
- 领取在同一写事务内校验调度租约，换手后的旧拥有者不能领取；安全关停等已发操作保存 ID/状态后才释放租约，运行中也恢复后来过期的旧租约。
- 请求参数 data_format/download_format 为源站产物格式与封装，仍保留，不代表本地下载开关。
- 结果 URL/文件名/大小/类型来自真实元数据，有效期未知留空；支持复制、CLI/API 输出与手动更新，失效不自动重提。不将完整签名链接或 API Key 写普通事件/日志。
- requests 配置保存前校验，app.yaml 用写锁串行合并并原子替换。同进程 PATCH 对后续领取和查询安排生效，已开始操作和已安排的等待照常执行；默认重试上限用于新建请求。独立 CLI 保存后由后台服务重启读取。CLI/API 不接受输出目录、覆盖或旧 enqueue/run 下载入口。
- 凭据仅放 secrets.yaml，Linux 用 0600、文件锁及原子替换。AI API Key 在本机同源设置页直接显示。日志、CLI 与常规 API 隐藏密钥。Windows 原生保护待验收。
- 不引入 Textual、旧 src/ui、固定 ERA5 字段、旧 YAML/JSON 任务导入、暂停/预约/可靠数据断点续传或展示性控制。

## 界面

默认 CDS；少于 5 项多选直接卡片，其余非变量枚举支持严格名称/ID 逗号输入；变量仅搜索并从候选选择，常驻标签一行起自动增高，候选 560px。
时间两行两列，组合输入即展开、等宽、行内箭头，可外部/Esc/按钮关闭；地图固定离线世界视图，区域框/点位随坐标变化，处理日界线和零度。
AI 极简输入和请求拆分与提交置右栏，宽屏固定并独立滚动，服务配置在设置。手动请求规模在拆分与提交卡片内，达到 50% 变黄、75% 变红。点击操作区按钮弹出请求详情，可逐份切换已选参数卡片和原始 JSON。移除本地输出目录、浏览和添加并下载。队列只交付链接，不跟踪外部下载进度。 提交操作区支持保存、预览、加载和删除预设，复用模板服务。
CDS 智能拆分按目标份数均衡有效时间点，优先保留同一天的时次。预览、创建与估算共享拆分计划，手动逐份估算后显示最大子请求及其上限，部分失败时不展示确定最大值。
队列表格跟随页面宽度，每页 10 条，底部显示当前范围与复制反馈。标题下显示“来源 · 数据集 ID”。行复选框悬停、聚焦或选中时显示，触屏常显，表头全选仅限当前页。刷新、复制、重试、取消和删除共用行内及批量操作条件。顶部刷新与复制在未勾选时作用于当前页符合条件的请求，批量重试、取消和删除须勾选，删除须确认。

## 文档与进度

- doc-1 / .backlog/docs/product/doc-1 - Product.md：当前功能、支持范围、限制和最新证据。
- doc-3：官方字段调查、显示/编码依据；旧本地输出和 ARCO 规则由 DRAFT-7 取代。
- DRAFT-7 / TASK-32：已批准的请求监视/链接路线与实施；TASK-9 为真实小请求到链接验收，不再验收下载内容。
- DRAFT-6 / TASK-30：通用模型与编译；TASK-31：CDS 工作区、手动规模及新提交入口。
- TASK-33（由 DRAFT-8 转入）：按份数智能拆分和最大子请求规模。
- TASK-29：两个 NCAR 目录和原文件链接；ARCO 本地导出取消。
- TASK-10/11：关停、租约及迟到恢复；TASK-13/14：配置校验与保存、凭据异常。
- DRAFT-1～5 保留原批准来源和仍有效要求，冲突下载要求注明取代，不冒充修复或重新验收。
- decision-1 为 CLI + 本地 Web；decision-2 为无 Alembic 的启动建表。
- doc-2 为历史验证，不能当当前实测；doc/note/cds_smoke_request.yaml 为有效请求附件。

## 验证与协作

先读当前 AGENTS、产品、相关任务、Git 历史和工作区，保护无关修改。用 uv 管理 Python、npm 管理前端。按改动做相关功能检查和必要构建，不自动跑无关全量测试或主动视觉验收。真实与模拟证据分开；不冒称全部数据集、科学文件内容、真实远端取消或 Windows 原生已验收。

Backlog 在 WSL 仓库根目录仅用 CLI，先检查 .backlog/config.yml；保留 Git、auto_commit:false、待验收，不重新 init、不用 MCP 或直接编辑 Markdown。基线 Backlog.md 1.55.2，无项目内 CLI 可用 npx --yes --package backlog.md@1.55.2 backlog，缓存后可 offline。

新需求先形成 Draft PRD，经用户确认后登记任务，实现前记录计划。验证后最多待验收，不代勾验收、不设 Done。取消旧需求须记录原因，不伪装完成；过时任务可 CLI 归档，删除依用户规则列清单确认。

启动 Dashboard 先查 Windows/WSL 两侧端口，复用同项目服务，否则选空闲端口，以 backlog browser --port <port> --non-interactive --no-open 启动，核实项目/地址后 open_in_codex，保留其他服务。

无 LAST_RUN/TODO/Roadmap 或迁移快照，不新建重复历史汇总；清理本轮临时脚本及可再生成缓存，保留运行资产、有效要求、验收证据和用户数据。版本、提交、Tag、发布分别要明确授权，CHANGELOG 只在更新版本时修改。本轮未授权提交/版本/发布。

最后更新：2026-11-02。
