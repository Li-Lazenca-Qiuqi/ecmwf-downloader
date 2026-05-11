# src/ 源代码目录

## 目录结构

```
src/
├── api/           # API抽象层
├── core/          # 核心业务逻辑层
├── ui/            # 用户界面层
└── utils/         # 工具模块
```

## 文件信息

### api/ - API抽象层

#### base.py
API客户端基类，定义统一的API接口规范。

- `BaseAPIClient`：抽象基类
  - `retrieve()`：下载数据的抽象方法
  - `get_status()`：获取请求状态
  - `get_client_info()`：获取客户端信息

#### cds_client.py
CDS API客户端实现，继承自BaseAPIClient。

- `CDSClient`：CDS API客户端
  - 认证：使用key（UUID格式）
  - `retrieve()`：提交下载请求
  - `get_status()`：查询请求状态
  - `delete_request()`：删除请求
- 依赖：`cdsapi`库

#### ecmwf_datastores_client.py
ECMWF数据存储统一客户端，支持多种数据源。

- `ECMWFDatastoresClient`：统一客户端
  - 支持CDS、ADS等多种数据源
  - 自动选择合适的API端点

---

### core/ - 核心业务逻辑层

#### exceptions.py
自定义异常类体系。

- `ECMWFDownloaderError`：基础异常
- `ConfigError`：配置错误
- `AccountError`：账号错误
- `DownloadError`：下载错误
- `ProgressError`：进度错误
- `ValidationError`：验证错误
- `APIError`：API错误

#### config.py
Pydantic配置模型定义。

- `AccountInfo`：账号信息（email, key, url）
- `DownloadConfig`：下载配置
- `AppConfig`：应用总配置
- 支持YAML序列化/反序列化

#### account_pool.py
账号池管理，支持多账号轮换。

- `AccountPool`：账号池管理器
  - `add_account()`：添加账号
  - `remove_account()`：移除账号
  - `get_next_account()`：获取下一个可用账号
  - `mark_account_busy()`：标记账号忙碌
- 线程安全设计

#### progress.py
任务进度管理器。

- `ProgressManager`：进度管理
  - `create_task()`：创建任务
  - `update_progress()`：更新进度
  - `get_task()`：获取任务信息
- 支持持久化存储

#### request_builder.py
请求参数构建器，支持不同拆分策略。

- `RequestBuilder`：请求构建器
  - `build_requests()`：构建请求列表
  - 支持按月/按年/不拆分策略
  - 自动处理日期范围

#### task_service.py
任务服务，统一的任务创建入口。

- `TaskService`：任务服务
  - `create_task()`：创建下载任务
  - 整合配置验证、请求构建、进度管理

#### ai_config.py
AI功能配置模型。

- `AIConfig`：AI配置
  - API端点、密钥、模型选择
  - 系统提示词配置

#### ai_generator.py
AI参数生成器，支持自然语言转配置。

- `AIGenerator`：AI生成器
  - `generate_params()`：生成参数配置
  - 支持OpenAI兼容API
- 依赖：`openai`库（可选）

#### dataset_schema.py
数据集模式定义和处理。

- `DatasetSchema`：数据集模式
  - 字段定义、验证规则
  - 动态表单生成支持

---

### ui/ - 用户界面层

#### app.py
TUI应用主入口。

- `ECMWFDownloaderApp`：Textual应用主类
  - 屏幕管理、主题配置
  - 全局状态管理
  - 配置初始化调用

#### screens/ - 屏幕模块

| 文件 | 功能 |
|------|------|
| `base_screen.py` | 屏幕基类，通用布局 |
| `home_screen.py` | 首页（统计卡片+快捷操作）|
| `tasks_screen.py` | 任务列表页 |
| `download_screen.py` | 下载管理页 |
| `accounts_screen.py` | 账号池管理页 |

#### dialogs/ - 对话框模块

| 文件 | 功能 |
|------|------|
| `base_dialog.py` | 对话框基类 |
| `account_dialog.py` | 账号添加/编辑对话框 |
| `request_preview_dialog.py` | 请求预览对话框 |

#### pages/ - 页面模块

| 目录/文件 | 功能 |
|-----------|------|
| `create_task/` | 创建任务页面（模块化）|
| `create_task/view.py` | 视图层 |
| `create_task/controller.py` | 控制器层 |
| `create_task/services/` | 服务层（AI填充、配置存储、模式获取）|
| `create_task/mappers/` | 数据映射层 |
| `create_task/dialogs/` | 对话框（AI生成、加载/保存配置）|

#### widgets/ - 自定义组件

| 文件 | 功能 |
|------|------|
| `navigation_sidebar.py` | 侧边栏导航 |
| `content_area.py` | 内容区域容器 |
| `account_table.py` | 账号表格 |
| `task_table.py` | 任务表格 |
| `dynamic_form_field.py` | 动态表单字段 |
| `contents/` | 各页面内容组件 |

#### workers/ - 后台任务

| 文件 | 功能 |
|------|------|
| `download_worker.py` | 下载执行Worker |

### utils/ - 工具模块

#### config_initializer.py
配置文件初始化器。

- `ConfigInitializer`：配置初始化
  - `ensure_config_files()`：确保配置文件存在
  - 从`.example`模板复制生成配置文件
