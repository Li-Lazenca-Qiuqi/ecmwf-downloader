---
id: TASK-19
title: 获取完整数据集字段与明确约束来源
status: Done
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-11-08T09:16:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - src/ecmwf_downloader/application/datasets.py
  - src/ecmwf_downloader/infrastructure/datastores.py
  - src/ecmwf_downloader/interfaces/cli/app.py
  - frontend/src/pages/RequestPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
  - .backlog/drafts/draft-4 - 添加任务字段选择、实时预览与年月日拆分.md
  - .backlog/drafts/draft-6 - PRD-数据集字段统一显示规则.md
  - .backlog/docs/notes/doc-3 - 数据集表单字段调查与展示规则依据.md
priority: medium
type: enhancement
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户已确认 DRAFT-4 恢复字段选择式编辑。原仅 JSON 与取消字段联动的范围被本稿替代；需要获取完整官方表单和选项，保留类型、字段标签与特殊控件信息，错误不静默替换为固定字段。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 全部字段和可选值完整可辨识，支持常用 CDS 控件及 JSON Schema 类型
- [ ] #2 在线、缓存及失败来源明确；约束查询不伪造成功，错误脱敏
- [ ] #3 使用真实公开元数据和模拟类型场景定向验证字段与约束，测试仅访问元数据
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 核对真实 CDS 表单结构并统一字段/选项类型；2. 明确元数据和约束来源，限制网络重试；3. 使用两类真实元数据及模拟异常定向验证。

按用户确认保留每个变量的所有官方分类，兼容现有 group 字段，增加去重及多分类定向验证。

按用户要求查询当前完整数据集目录与各数据集官方表单，统计控件、分组、日期、区域和选项规模，查找当前映射的遗漏；依据实际覆盖形成统一展示规则草稿，单独记录无法获取的表单，不改下载数据与用户配置。

用户已批准实施 DRAFT-6，接入统一 schema、分组、请求编译和通用控件，验证后提交用户验收，保留已有工作区改动。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 根据新技术路线缩小范围：撤销旧字段表单补齐和约束联动要求；JSON 编辑由 TASK-17 承接。源码核对仍有 except 后静默返回固定 fields / 空 constraints，且 AI 和 CLI/API 仍使用该查询，因此本任务保留 To Do，不能因移除表单就判定问题消失。

2026-10-26 已完成 DRAFT-4 实施：完整在线字段、来源/缓存/错误说明；选择式控件与顶部 AI、实时只读预览；后端目录浏览；year/month/day 拆分及日历警告。34 项相关后端测试、TypeScript/Vite 构建和隔离 Playwright 功能检查通过，含搜索/批选、类型、目录、AI 过期/无效防护及创建 queued。真实只读核对 ERA5 single levels 为 12 字段/262 变量、ERA5-Land 月平均为 11 字段/60 变量且无日字段；本机 API 已验证。没有真实下载、外部 AI 调用、视觉或 Windows 原生验收。用户数据与账号页既有改动保留，未提交，验收项未勾选。

用户要求的变量分类已实现：groups 完整保留多分类，group 保持首类兼容；折叠分组、组内计数/全选/清空，全局名称/ID/分类搜索自动展开，跨组选择同步且请求值唯一。16 项定向后端测试与 TS/Vite 构建通过；公开及本机 API 验证 262 变量/15 分类/279 分类关系，17 个变量有多分类。Playwright CLI 真实字段配合模拟约束与预览通过 11 项功能检查，覆盖默认折叠、批选/清空、跨组同步、搜索与去重、平铺兼容及窄屏操作，无页面或控制台错误；无截图/视觉验收。服务已更新且调度正常，未创建真实下载任务，未提交，仍交用户验收。

全量官方目录调查：145 项已逐项请求，144 份表单有效、1 项 404，10 种控件共 1268 项。发现 ExclusiveGroupAccordionWidget 涉及 12 个数据集、DateRangeWidget 和 GeographicLocationWidget 各涉及 7 个数据集仍被标为 unsupported；children 为 102 个字符串引用，目前扁平映射没有保留互斥语义。FreeEdition 还包含层次单位和下载指引，不能一律隐藏；50 个区域字段有 10 个非全球默认值。为避免以抽样结果代表全部支持，将本任务退回 In Progress，验收项保持未勾选。调查证据见 doc-3，展示规则提案见 DRAFT-6，仅调查与设计，应用未改动，后续按用户审查结果实施。

按用户要求将 DRAFT-6 扩展为完整通用方案，覆盖范围、结构模型、10 类控件与 JSON Schema、互斥组、时间/空间、约束、请求编译、来源能力、AI/CLI、异常状态、模块接口、分阶段交付及 12 项验收标准。明确 UI 单选与 API 数组是不同维度，未核实编码以 partial 追踪。方案经 CLI 写入并读回核对，未按本稿实施应用、未提交 Git，任务继续 In Progress。

用户批准的 DRAFT-6 已由 TASK-30 完成通用字段与请求编译实施。当前全量分类 144 份有效表单、1268 节点均被识别；82 个不同定向后端测试分批通过，构建及 16 组页面交互检查通过。普通 ERA5 和 timeseries 在线字段/真实本地预览均 HTTP 200，未创建生产下载或调用真实 AI。完整证据与边界见 TASK-30、Product；继续由用户验收，验收项不勾选，未提交。

2026-10-28 DRAFT-7 已获用户确认并实施于 TASK-32：软件不再本地下载，移除输出目录/浏览/覆盖/传输进度及旧 enqueue/run 入口；保留自动提交、字段、AI、预览和请求日期拆分。原用户完成状态与验收记录不改写，冲突旧条款不作为当前验收要求。
<!-- SECTION:NOTES:END -->
