# ECMWF Downloader

一个用于自动化下载ECMWF（欧洲中期天气预报中心）气象数据的Python工具。

## 项目背景信息

ECMWF（European Centre for Medium-Range Weather Forecasts）提供全球领先的气象数据和预报服务。本项目旨在开发一个便捷的工具，帮助研究人员和开发者高效获取ECMWF Climate Data Store (CDS)中的气象数据，支持气象研究、气候分析和业务应用。

## 目录结构

```
ECMWF downloader/
├── AGENTS.md                     # 项目级长期记忆
├── config/                       # 配置文件目录
│   ├── *.yaml.example            # 配置模板文件
│   └── *.yaml                    # 实际配置文件（git忽略）
├── src/                          # 源代码目录
│   ├── api/                      # API抽象层
│   │   ├── base.py               # API客户端基类
│   │   ├── cds_client.py         # CDS API客户端
│   │   └── ecmwf_datastores_client.py
│   ├── core/                     # 核心业务逻辑层
│   │   ├── exceptions.py         # 自定义异常类
│   │   ├── config.py             # Pydantic配置模型
│   │   ├── account_pool.py       # 账号池管理
│   │   ├── progress.py           # 进度管理器
│   │   ├── request_builder.py    # 请求构建器
│   │   ├── task_service.py       # 任务服务
│   │   ├── ai_config.py          # AI配置
│   │   ├── ai_generator.py       # AI参数生成
│   │   └── dataset_schema.py     # 数据集模式
│   ├── ui/                       # 用户界面层
│   │   ├── app.py                # TUI应用主入口
│   │   ├── screens/              # 屏幕模块
│   │   ├── dialogs/              # 对话框模块
│   │   ├── widgets/              # 自定义组件
│   │   ├── pages/                # 页面模块
│   │   └── workers/              # 后台任务
│   └── utils/                    # 工具模块
│       └── config_initializer.py # 配置初始化
├── tests/                        # 测试目录
│   ├── test_core/                # 核心模块测试
│   ├── test_api/                 # API模块测试
│   └── test_ui/                  # UI模块测试
├── README.md                     # 项目说明
└── CHANGELOG.md                  # 版本更新日志
```

最后更新：2026-05-11，对应版本：v0.4.1。

## 技术栈与技术路线

### 核心技术

- **标准运行环境**：Linux
- **语言**：Python 3.9+
- **主要依赖**：
  - `cdsapi` - ECMWF CDS数据下载API客户端
  - `pydantic` - 配置验证和数据模型
  - `PyYAML` - YAML配置文件解析
  - `pytest` - 单元测试框架
  - `textual` - TUI终端界面框架
  - `openai` - AI参数生成（可选依赖）

### 技术架构

```
配置层 → API抽象层 → 数据下载层 → 进度管理层
  ↓         ↓           ↓            ↓
YAML    BaseAPIClient  CDSClient  ProgressManager
```

### 技术路线

1. 使用ECMWF Climate Data Store (CDS) API进行数据请求
2. 支持多种气象数据集（ERA5、ERA5-Land等）
3. 提供YAML配置文件管理下载参数
4. 实现多账号轮换和并发下载
5. 支持断点续传和进度持久化
6. 支持AI自然语言转参数配置

## 当前状态

**版本**：v0.4.1

**阶段**：第五阶段（下载功能集成）**进行中**

**已实现功能**：
- ✅ 核心模块（异常类、配置模型、账号池、进度管理、存储层）
- ✅ API抽象层（基类、CDS客户端、ECMWF客户端）
- ✅ 请求构建与任务服务
- ✅ AI参数生成（支持自然语言转配置）
- ✅ TUI终端界面（首页、任务、下载、账号、配置页面）
- ✅ 账号管理（添加/编辑/启用/禁用/删除）
- ✅ 配置管理（创建任务 + 预览功能）
- ✅ 配置初始化（example模板自动复制）
- ✅ 任务持久化（崩溃恢复）
- ✅ 任务状态扩展（QUEUED 入队状态）
- ✅ 存储层抽象（TaskStore 接口）
- ✅ 状态机机制（合法转换校验）
- ✅ 崩溃恢复（启动时自动修复状态）
- ✅ 队列调度器（并发限流、账号分配）

## 工作阶段

- [x] 第一阶段：核心模块重构
- [x] 第二阶段：TUI基础框架
- [x] 第三阶段：TUI测试与完善
- [x] 第四阶段：功能完善与优化
- [ ] 第五阶段：核心下载功能集成
  - [x] 请求构建器模块
  - [x] 任务服务模块
  - [x] 请求预览对话框
  - [x] AI参数生成功能
  - [x] 账号系统重构（uid→email）
  - [x] 配置系统重构（example模板）
  - [x] 任务持久化与观察者重构
  - [x] 任务状态扩展（QUEUED）
  - [x] 存储层抽象（TaskStore）
  - [x] 状态机机制（VALID_TRANSITIONS）
  - [x] 崩溃恢复（reconcile）
  - [x] 多文件存储集成
  - [x] 队列调度器
  - [ ] 集成下载Worker与控制按钮
  - [ ] 实现批量下载功能

## 使用方法

### Linux 环境准备

推荐使用 `uv` 管理虚拟环境与依赖：

```bash
cd /path/to/ecmwf-downloader
uv sync --extra dev
```

如果需要使用 AI 参数生成功能：

```bash
uv sync --extra dev --extra ai
```

### 运行

```bash
uv run ecmwf
# 或
uv run python -m src.ui
```

### 测试

```bash
uv run --extra dev pytest
```

### 配置

首次运行会自动从 `config/*.yaml.example` 复制生成配置文件：
- `config/default_config.yaml` - 主配置文件
- `config/accounts.yaml` - 账号池配置
- `config/ai_config.yaml` - AI功能配置

## 资源

### 官方资源

- [ECMWF Climate Data Store](https://cds.climate.copernicus.eu/) - 数据下载平台
- [CDS API使用指南](https://cds.climate.copernicus.eu/api-how-to) - API配置教程
- [ECMWF数据集目录](https://cds.climate.copernicus.eu/datasets) - 可用数据集列表

### 开发资源

- [cdsapi Python库文档](https://pypi.org/project/cdsapi/)
- [ECMWF API文档](https://confluence.ecmwf.int/display/CKB/Climate+Data+Store+%28CDS%29+API)
- [ERA5数据文档](https://confluence.ecmwf.int/display/CKB/ERA5+data+documentation)

## 许可证

待定

## 联系方式

待定
