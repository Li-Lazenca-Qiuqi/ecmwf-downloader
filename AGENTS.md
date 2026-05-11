# ECMWF Downloader

## 项目背景信息

ECMWF（European Centre for Medium-Range Weather Forecasts，欧洲中期天气预报中心）提供全球领先的气象数据和预报服务。本项目旨在开发一个Python工具，用于自动化下载和管理ECMWF的气象数据，支持气象研究、气候分析和业务应用。

## 目录结构

```
ECMWF downloader/
├── AGENTS.md                     # 项目级长期记忆
├── config/                       # 配置文件目录
├── data/                         # 数据存储目录
├── logs/                         # 日志目录
├── src/                          # 源代码目录
├── tests/                        # 测试目录
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
└── CHANGELOG.md                  # 更新日志
```

最后更新：2026-05-11，对应版本：v0.4.1。

## 技术栈与技术路线

- **标准运行环境**：Linux
- **语言**：Python 3.9+
- **核心依赖**：
  - `cdsapi` - ECMWF CDS API客户端
  - `pydantic` - 配置验证
  - `PyYAML` - YAML配置解析
  - `pytest` - 单元测试框架
  - `textual` - TUI框架
  - `openai` - AI参数生成（可选）

- **技术路线**：
  1. 使用ECMWF CDS API下载数据
  2. 支持多账号轮换提高下载效率
  3. 支持断点续传和批量下载
  4. 提供配置化的请求参数管理
  5. 支持AI自然语言转参数配置

## 当前状态

**版本**：v0.4.1

**阶段**：第五阶段（下载功能集成）**进行中**

**已完成的模块**：
- ✅ 核心模块（exceptions, config, account_pool, progress, progress_store）
- ✅ API层（base, cds_client, ecmwf_datastores_client）
- ✅ 请求构建与任务服务（request_builder, task_service）
- ✅ AI参数生成（ai_config, ai_generator, dataset_schema）
- ✅ TUI界面（screens, dialogs, widgets, pages）
- ✅ 配置初始化（config_initializer）
- ✅ 任务状态扩展（QUEUED 状态）
- ✅ 存储层抽象（TaskStore 接口）
- ✅ 状态机机制（VALID_TRANSITIONS）
- ✅ 崩溃恢复逻辑（reconcile）
- ✅ 队列调度器（DownloadQueueScheduler）

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

## 资源

- [ECMWF Climate Data Store (CDS)](https://cds.climate.copernicus.eu/)
- [CDS API文档](https://cds.climate.copernicus.eu/api-how-to)
- [cdsapi Python库](https://pypi.org/project/cdsapi/)
