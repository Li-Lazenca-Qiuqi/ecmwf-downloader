---
id: TASK-15
title: 统一任务创建即入队与取消行为
status: Done
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T16:01:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/lib/api.ts
  - src/ecmwf_downloader/application/services.py
  - src/ecmwf_downloader/infrastructure/repositories.py
  - src/ecmwf_downloader/interfaces/cli/app.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
  - .backlog/drafts/draft-3 - 单一下载队列与自动开始需求.md
priority: medium
type: bug
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户已批准 DRAFT-3：新任务不再先保存为待入队，CLI/API/Web 统一自动入队。原仅创建 pending 的验收要求被新需求取代。历史 pending 保留，旧 enqueue 入口仅作兼容，不自动启动历史记录。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CLI/API/应用服务创建的新任务原子写入 queued，无需二次入队；预览不写任务
- [ ] #2 保留单一队列及并发上限，取消的任务不被领取、不自动重试、不发布成功文件
- [ ] #3 不改数据库结构与历史 pending；兼容规则、后台消费者要求明确；定向测试通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository 创建直接写 queued，移除服务创建时的待入队分支；旧入队命令隐藏兼容，API 显式拒绝 enqueue=false。
2. 收紧取消、重试与最终文件发布的事务边界，覆盖运行与取消竞态。
3. 隔离目录测试 API/CLI 自动入队、并发排队、取消及历史 pending 保持，更新文档。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 完成单一队列与整体界面简化。相关后端 24 项通过（含新建即 queued、API 拒绝延后、CLI、并发、取消/完成竞态和历史 pending）；TypeScript/Vite 构建通过。隔离 Playwright 功能检查通过搜索、筛选、分页、详情、取消、JSON 校验、预览无写入、添加即入队、账号新增/编辑/禁用/状态重置、实际设置、旧路由跳转与窄屏导航；仅主动模拟 422 产生预期资源错误。没有真实 CDS 请求、视觉验收或 Windows 原生验收。实际 8000 服务已更新、健康且调度器运行，配置与用户任务数据保留。未提交，验收项保持未勾选。

2026-10-25 技术路线复核：旧“仅创建 pending、手动稍后入队”要求已取消并改写为本任务当前验收；新任务立即 queued，历史 pending 的显式兼容不属于新增产品入口。不把本任务归档或标完成，继续交用户验收。
<!-- SECTION:NOTES:END -->
