# Changelog

## 0.5.0 2026.08.17 CLI + Web 架构重构

### 重大变更

- 移除 Textual TUI、`src/ui/` 及对应 UI 测试，入口改为 `ecmwf_downloader` 标准包。
- 新增 Typer CLI、FastAPI `/api/v1` REST/SSE 和 React + TypeScript + Vite 管理台；前端静态产物随 wheel 发布。
- 用 SQLAlchemy + SQLite（WAL、外键、busy timeout）替代多文件任务 JSON，新增任务事件、调度租约、账号运行状态和请求模板表。
- 下载 Worker 脱离 UI，使用数据库租约、心跳、崩溃恢复、`.part` 文件和原子重命名。
- 请求模型改为通用 `dataset_id + request_payload`，支持不拆分、按年、按月；取消只在安全点生效，首版不提供暂停/续传。
- CDS/AI 凭据迁移到独立且权限为 `0600` 的 `config/secrets.yaml`，接口和日志不返回完整密钥。

### 不兼容说明

- Python 最低版本提升至 3.11；版本号提升至 0.5.0。
- 新版本使用全新 SQLite 数据库，不导入旧 YAML/JSON 任务历史，也不自动删除旧配置和任务文件。
- 旧 TUI 命令不再提供；请使用 `ecmwf web`、`ecmwf worker` 或 `ecmwf task ...`。

## 0.4.1 2026.02.23 队列调度器集成与多选修复

### 新增功能

1. **新增**：队列调度器模块
   - `DownloadQueueScheduler` 类负责队列消费和下载调度
   - 支持并发限流、账号分配、退避过滤
   - 线程安全设计，使用 RLock 保护内部状态

2. **新增**：UI 集成队列调度器
   - `ECMWFDownloaderApp` 新增 `queue_scheduler` 属性
   - 任务页"开始下载"改为"入队"操作（PENDING→QUEUED）

### 重构

1. **重构**：存储层简化
   - 移除 `SingleFileTaskStore`，统一使用 `MultiFileTaskStore`
   - 简化存储层接口，只保留 `TaskStore` 基类和 `MultiFileTaskStore`

2. **重构**：下载 Worker 改为函数式 API
   - 适配调度器回调机制
   - 参数传递 app 实例

### Bug 修复

1. **修复**：任务管理页面多选功能
   - 修复 `progress_path` 参数名错误（改为 `data_dir`）
   - 实现鼠标点击切换选中状态，移除键盘操作
   - 选中标志从 `[x]`/`[ ]` 改为 `✓`/`○`，避免富文本解析问题

### 其他

1. **改进**：任务管理 UI
   - 侧边栏和页面标题改为"任务管理"
   - 操作按钮扩展为 5 个：全选、入队、重试、取消、删除

2. **清理**：删除临时工作文件和缓存

---

## 0.4.0 2026.02.23 状态机机制与崩溃恢复

### 新增功能

1. **新增**：状态机机制
   - `VALID_TRANSITIONS` 定义合法状态转换路径
   - `can_transition()` 方法校验转换合法性
   - `transition()` 安全状态转换，失败抛 `ValueError`

2. **新增**：崩溃恢复逻辑
   - `reconcile()` 方法修复非持久状态
   - 启动时自动将 QUEUED/DOWNLOADING/RETRYING 重置为 PENDING
   - 完整清理运行时字段（progress、account_id、error_message 等）

3. **新增**：重试退避机制
   - `next_retry_at` 字段记录下次重试时间
   - 调度器过滤未到时间的 RETRYING 任务
   - 退避策略：5s → 15s → 60s

4. **新增**：原子化 `retry_task()` 方法
   - 单锁内完成"重置字段 + 转 PENDING + 入队"
   - 避免中间态落盘和多次通知
   - `can_transition()` 断言检查确保状态机规则一致性

### 重构

1. **重构**：`update_status()` 添加日志告警
   - 提醒开发者优先使用 `transition()`
   - 告警位置在确认任务存在之后，避免噪声

2. **重构**：持久化异常添加日志
   - `transition()`、`delete_task()`、`load()` 等方法添加 `logger.error()`
   - 提升可观测性，便于问题排查

3. **重构**：`reset_task_for_retry()` 明确边界
   - 文档说明适用场景
   - 推荐常规重试使用 `retry_task()`

### Bug 修复

1. **修复**：transition 落盘并发乱序风险
   - 将 `save_task()` 移到锁内执行
   - 避免多线程下状态乱序覆盖

2. **修复**：调度器回退绕过状态机
   - 添加 `DOWNLOADING → QUEUED` 合法转换路径
   - 启动失败时优先走 `transition()`

3. **修复**：UI 重试未重置 retry_count
   - 新增 `reset_task_for_retry()` 方法
   - 重试时清零 `retry_count` 和运行时字段

4. **修复**：delete_task 未持久化
   - 调用存储层 `delete_task()` 同步删除磁盘记录
   - 避免重启后任务"复活"

### 测试更新

1. **新增**：363 个测试用例
   - 测试覆盖状态机、崩溃恢复、持久化等场景
   - Codex 审查评分：63 → 93/100

---

## 0.3.0 2026.02.22 任务状态扩展与存储层重构

### 新增功能

1. **新增**：QUEUED 任务状态
   - TaskStatus 枚举新增 `QUEUED = "queued"` 状态
   - 表示任务已入队等待调度
   - 状态流转：PENDING → QUEUED → DOWNLOADING → COMPLETED/FAILED/CANCELLED

2. **新增**：任务存储层抽象
   - 新建 `src/core/progress_store.py` 模块
   - `TaskStore` 抽象基类定义统一存储接口
   - `SingleFileTaskStore` 单文件 JSON 存储实现
   - `MultiFileTaskStore` 多文件存储实现

### 重构

1. **重构**：任务持久化机制
   - TaskService 创建任务后立即持久化
   - save() 失败时回滚内存状态（事务一致性）
   - 批量创建保证原子性

2. **重构**：观察者通知机制
   - 新增 `TaskEventType` 枚举（CREATED/UPDATED/DELETED）
   - 锁外通知观察者，解决多线程死锁问题
   - UI 根据事件类型处理，避免反查 ProgressManager

3. **重构**：项目记忆系统
   - CLAUDE.md 重构为标准格式
   - README.md 重构为标准格式
   - 新增 `src/CLAUDE.md` 子目录记忆

### 多文件存储设计

```
data/
├── pending_tasks.json     # PENDING 状态
├── queued_tasks.json      # QUEUED 状态
├── downloading_tasks.json # DOWNLOADING, RETRYING 状态
└── finished_tasks.json    # COMPLETED, FAILED, CANCELLED 状态
```

### UI 更新

- 所有状态映射统一添加 QUEUED（颜色：cyan，文本："已入队"）
- 筛选映射添加 queued 选项

---

## 0.2.3 2026.02.20 账号系统重构与配置系统优化

### 重构

1. **重构**：账号系统 uid → email
   - API 认证改为仅使用 `key`（UUID 格式）
   - `AccountInfo.uid` 改为 `AccountInfo.email`（必填，用于显示标识）
   - 使用邮箱作为账号唯一标识
2. **重构**：配置系统
   - 创建 `config/*.example` 模板文件
   - 新增 `src/utils/config_initializer.py` 配置初始化模块
   - 应用启动时自动从 example 复制生成配置文件
   - 更新 `.gitignore` 忽略 `config/*` 但保留 `*.example`

### UI 优化

1. **优化**：侧边栏和首页"账号"改为"账号池"
2. **优化**：账号表格移除"账号ID"列
3. **优化**：账号对话框移除账号ID输入框

### Bug 修复
1. **修复**：`accounts.yaml.example` 空列表导致 None 解析错误
2. **修复**：`AccountTable.get_selected_account_id` 行号映射正确性
3. **修复**：`account_pool.py` None 迭代防护
4. **修复**：文档字符串与实现不一致（email 必填说明）
5. **修复**：移除未使用的 `email` 变量

### 测试更新
- 更新 7 个测试文件以匹配新的账号模型

---

## 0.2.2 2026.02.20 配置页面重构与Bug修复

### 重构
1. **重构**：配置页面模块化重构
   - 将 1247 行单体文件拆分为 13 个模块化文件
   - 职责分离：View / Controller / Services / Mappers / Dialogs
   - 新增 `src/ui/pages/create_task/` 模块目录
   - 保留 `ConfigContent` 兼容性别名

### 新增功能
1. **新增**：配置加载后恢复静态字段（dataset/output_dir/strategy）
2. **新增**：AI 生成结果同步到动态字段控件
3. **新增**：Python 3.8 类型注解兼容（`Tuple[...]` 替代 `tuple[...]`）

### Bug 修复
1. **修复**：清空按钮闪退问题（Select 组件清空逻辑）
2. **修复**：预览对话框确认按钮无响应问题（改用回调模式）
3. **修复**：加载配置时 widget ID 冲突问题
4. **修复**：创建任务前缺少 dataset 非空校验

### 优化
1. **优化**：按钮布局改为均匀分布
2. **优化**：静默吞错改为日志告警
3. **优化**：移除未使用的回调接口（`on_constraints_updated`）

### 代码质量
- Codex 审查评分：66/100 → 96/100

---

## 0.2.1 2026.02.18 第五阶段进行中（下载功能集成）

### 新增功能
1. **新增**：AI 参数生成功能
   - 支持自然语言转参数配置
   - 支持 OpenAI 兼容 API（智谱 AI、OpenAI、Ollama 等）
   - 可自定义系统提示词
   - 新增 `config/ai_config.yaml` 配置文件
2. **新增**：下载功能集成（第五阶段核心模块）
   - 添加开始下载按钮
   - 实现 JSON 序列化修复
3. **新增**：动态表单系统完善
   - UI 优化与配置管理功能
   - 字段类型扩展

### Bug 修复
1. **修复**：在线加载与动态表单字段选择问题
2. **修复**：快速多选模式与纯下拉控件行为优化
3. **修复**：气压层下拉栏按字符串排序的问题（改为智能数值排序）
4. **修复**：JSON 序列化问题
5. **修复**：用户配置文件从 git 追踪中移除

### 优化
1. **优化**：下拉选择框样式
2. **优化**：配置持久化逻辑重构
3. **优化**：TUI 界面优化与问题修复
4. **优化**：添加依赖与清理 CSS

### 依赖更新
1. **新增**：`openai` 可选依赖（用于 AI 生成功能）

---

## 0.2.0 2026.02.17 第四阶段完成（功能完善）

### 新增功能
1. **新增**：账号管理对话框模块（`src/ui/dialogs/`）
2. **新增**：可复用的模态对话框基类（`BaseDialog`）
3. **新增**：账号添加对话框，支持表单验证和密码掩码
4. **新增**：账号编辑对话框，编辑时保留统计数据
5. **新增**：操作回滚机制，保存失败时自动恢复状态
6. **新增**：对话框滚动支持（`overflow-y: auto`）
7. **新增**：`ecmwf` 启动命令

### TUI 界面完善
1. **优化**：键盘导航和焦点管理全面优化
2. **优化**：首页布局优化
3. **优化**：任务页布局调整
4. **优化**：下载页布局重构
5. **优化**：账号页布局修复
6. **优化**：配置页布局调整
7. **优化**：侧边栏样式优化

### Bug 修复
1. **修复**：空账号池导致应用闪退问题
2. **修复**：Textual CSS 兼容性问题（移除 `border-radius`、`box-shadow`）
3. **修复**：YAML 序列化枚举值问题
4. **修复**：UI 导航和表格操作的多个严重 Bug
5. **修复**：下载页右侧空白问题
6. **修复**：退出后终端卡住问题

### 技术改进
1. **优化**：使用 `model_dump(mode='json')` 确保枚举正确序列化
2. **优化**：使用 `yaml.safe_dump()` 避免 Python 特定标签
3. **优化**：移除 `AccountPool.__init__` 中的强制验证，采用延迟验证
4. **优化**：Textual CSS 使用显式 ID 选择器

---

## 0.1.0 2026.02.15 第三阶段完成（TUI 测试与完善）

### TUI 基础框架
1. **新增**：TUI 应用主入口（`src/ui/app.py`）
2. **新增**：基础屏幕类（`BaseScreen`）
3. **新增**：五个页面屏幕（首页、任务、下载、账号、配置）
4. **新增**：自定义组件（任务表格、账号表格）
5. **新增**：主题样式系统（`src/ui/styles/theme.py`）
6. **新增**：侧边栏导航组件

### 布局优化
1. **优化**：账号页表格和按钮区紧贴侧边栏
2. **优化**：下载页布局重构，合并卡片
3. **优化**：进度条占满剩余宽度
4. **优化**：统计项并排显示

### 测试
1. **新增**：UI 组件测试（任务 2-4）
2. **新增**：端到端测试报告
3. **新增**：导航测试适配新架构

---

## 0.0.1 2026.01.21 项目初始化

### 新增功能
1. **新增**：初始化Git仓库
2. **新增**：创建项目记忆组件（CLAUDE.md、README.md、CHANGELOG.md等）
3. **新增**：创建.claude目录结构
4. **新增**：创建TASKS.json任务清单
5. **新增**：创建.gitignore配置文件
6. **新增**：项目开发规划文档

### 布局优化
1. **修复**：账号页表格和按钮区未紧贴侧边栏的问题
2. **优化**：下载页布局重构，合并两个卡片为一个进度信息卡片
3. **优化**：下载页进度条占满剩余宽度
4. **优化**：下载页统计项改为5项并排（总文件、下载中、已完成、排队中、失败）
5. **优化**：调整表格高度，减少按钮区域间距

### Bug 修复
1. **修复**：下载页右侧空白问题（CSS `:not()` 选择器兼容性）
2. **修复**：退出后终端卡住问题（观察者退出处理优化）

### 技术改进
1. **优化**：Textual CSS 避免使用复杂选择器，改用显式 ID 选择器
2. **优化**：观察者模式增加卸载态保护，防止退出阶段回调阻塞
3. **优化**：表格列宽刷新防抖，避免布局事件风暴
