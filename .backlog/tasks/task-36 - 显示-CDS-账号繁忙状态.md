---
id: TASK-36
title: 显示 CDS 账号繁忙状态
status: 待验收
assignee:
  - '@Codex'
created_date: '2026-11-08T13:54:00Z'
updated_date: '2026-11-08T13:56:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/AccountsPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
账号页需要区分可用且空闲的账号与正在处理 CDS 请求或测试连接的账号。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 可用账号在绑定请求处于提交、远端排队/处理、刷新或取消时显示繁忙，全部相关操作结束后恢复可用。
- [ ] #2 当前正在测试的账号显示繁忙。禁用和连接异常继续表达账号状态，账号选择策略保持原口径。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
从已绑定账号的活动请求派生繁忙标志，复用现有 SSE 和轮询更新。验证请求状态及测试连接进度对账号行的展示。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
账号 API 从绑定的活动请求查询 is_busy。7 项定向后端测试通过，覆盖本地未绑定、提交、远端排队/运行、同账号多请求、取消、刷新和失效。前端构建通过，使用 Edge Playwright 模拟账号和 SSE，确认繁忙/可用更新、正在测试的账号显示繁忙、禁用与异常优先。8000 实例重启后确认调度正常、原 3 条请求仍在、真实账号 API 已返回状态标志。未创建真实远端请求。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
账号页已显示繁忙。活动请求或当前页面正在测试连接时，启用账号显示繁忙，操作全部结束后恢复可用。
<!-- SECTION:FINAL_SUMMARY:END -->
