---
id: TASK-17
title: 按单一队列简化整个管理台
status: 待验收
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T16:04:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/lib/api.ts
  - .backlog/docs/product/doc-1 - Product.md
  - frontend/src/pages/QueuePage.tsx
  - frontend/src/pages/RequestPage.tsx
  - frontend/src/pages/AccountsPage.tsx
  - frontend/src/pages/SettingsPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
  - .backlog/drafts/draft-3 - 单一下载队列与自动开始需求.md
priority: medium
type: enhancement
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户已批准 DRAFT-3，并要求全部简化现有界面。合并概览、任务与活动为一个队列页面；保留添加任务、账号、设置。去除假筛选、假状态、装饰性步骤与重复控制，保留可用功能及清晰错误反馈。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 导航收敛为队列、添加任务、账号、设置；旧首页/活动地址进入同一队列；不出现暂停、全局停止或手动入队控制
- [ ] #2 队列搜索、状态筛选、分页、详情、取消与失败重试均有实际行为；展示真实服务状态与等待原因
- [ ] #3 创建页仅保留一个提交入口，预览不写任务；账号和设置去除无效控件并保留实际可用操作；窄屏结构可用
- [ ] #4 前端类型检查/构建及定向功能检查通过，同源发布资源更新；不自动视觉测试
- [ ] #5 账号新建默认可用、编辑可启禁用；切换对象不残留表单且不回填密钥；保存与连接检查有可见成败反馈（承接 TASK-16 的有效范围）
- [ ] #6 连接与内置调度器状态、并发、输出目录、重试和 AI 启用取实际响应；异常和未知状态不显示为健康（承接 TASK-18）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 收敛导航和页面：队列首页、添加、账号、设置，复用现有色彩与组件依赖。
2. 单队列接入真实统计、筛选分页与任务详情；创建页折叠高级配置和 AI，保留可编辑请求参数与预览。
3. 简化账号和只读设置，移除无效控制及固定健康文案，补充加载/错误状态和窄屏布局。
4. 类型检查并生成实际托管资源，用隔离服务测试页面资源与核心交互，不做视觉验证。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 完成单一队列与整体界面简化。相关后端 24 项通过（含新建即 queued、API 拒绝延后、CLI、并发、取消/完成竞态和历史 pending）；TypeScript/Vite 构建通过。隔离 Playwright 功能检查通过搜索、筛选、分页、详情、取消、JSON 校验、预览无写入、添加即入队、账号新增/编辑/禁用/状态重置、实际设置、旧路由跳转与窄屏导航；仅主动模拟 422 产生预期资源错误。没有真实 CDS 请求、视觉验收或 Windows 原生验收。实际 8000 服务已更新、健康且调度器运行，配置与用户任务数据保留。未提交，验收项保持未勾选。

2026-10-25 按用户要求整理技术路线后的任务列表：TASK-16、TASK-18 的有效验收并入本任务，旧任务以 merged 标签归档，未标记完成。新建账号选择禁用的要求随无效选项一起取消，改为默认可用、编辑时可禁用。保留表单重置、凭据保护、错误反馈和真实状态展示的验收责任。未勾选任何验收项。

2026-10-26：用户已操作管理台，表示稍后提供 TASK-17 反馈，本次明确授权 Git 提交。保留待验收状态，不将提交或试用视为验收通过；其余用户手动设置的 Done 状态完整保留。
<!-- SECTION:NOTES:END -->
