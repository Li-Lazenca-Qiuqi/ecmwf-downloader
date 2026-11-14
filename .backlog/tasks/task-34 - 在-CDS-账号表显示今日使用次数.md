---
id: TASK-34
title: 在 CDS 账号表显示今日使用次数
status: Done
assignee:
  - '@Codex'
created_date: '2026-11-08T13:07:00Z'
updated_date: '2026-11-11T06:31:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/AccountsPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
账号列表需要查看当日使用量和最后使用时间，API 地址集中在账号表单中维护。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 账号表按后台本地自然日统计首次取得结果链接的 CDS 请求，刷新结果不重复计数。
- [ ] #2 账号表保留最后使用列，API 地址仅在添加或编辑账号的表单中显示。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
沿用请求事件记录记账账号和时间，查询当日成功次数并兼容可归属的旧记录。更新账号表格并验证跨日、刷新和删除请求的计数。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
按后台本地午夜统计首次就绪的 CDS 请求。使用现有请求事件存储，新事件可在删除请求后计数，旧事件仅回溯能确认账号的最后一次提交。累计值继续供现有 API/CLI 使用。定向测试 7 项通过，覆盖跨日、旧记录、刷新去重和删除后计数。TypeScript/Vite 构建通过，8000 实例已重启并核对账号 API、前端资源和原队列。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
账号列表显示今日使用次数与最后使用，API 地址在账号表单维护。按后台本地自然日统计，已验证并部署到本地实例。
<!-- SECTION:FINAL_SUMMARY:END -->
