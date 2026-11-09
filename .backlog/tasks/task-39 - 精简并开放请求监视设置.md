---
id: TASK-39
title: 精简并开放请求监视设置
status: 待验收
assignee:
  - '@Codex'
created_date: '2026-11-09T12:02:00Z'
updated_date: '2026-11-09T12:04:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/SettingsPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
设置首页只提供日常监视需要的查询间隔和默认重试上限。并行上限、重试等待、数据库路径从页面移出。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 页面可编辑并保存状态查询间隔与查询重试上限，验证范围与生效说明匹配后端。
- [ ] #2 页面隐藏并行上限、重试等待和数据库路径，保存只更新用户修改的监视参数。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用现有设置 PATCH，在首页提供两个数字字段及保存反馈；验证隔离配置和浏览器交互。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
前端构建通过。1200px 与 375px 浏览器模拟接口验证只展示两项、数字范围限制、部分 PATCH、保存失败保留草稿和刷新后读取。隔离 FastAPI/SQLite 验证部分写入不改并行/退避/数据库/AI、无效设置拒绝及新旧请求默认重试行为。没有更改运行实例的实际监视数值。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
设置首页仅显示可编辑的状态查询间隔与查询重试上限，复用现有设置校验和持久化。已通过功能检查，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
