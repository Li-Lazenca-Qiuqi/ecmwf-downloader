---
id: TASK-37
title: 完善列表全选、请求删除和并发连接测试
status: 待验收
assignee:
  - '@Codex'
created_date: '2026-11-09T11:13:00Z'
updated_date: '2026-11-09T11:18:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/QueuePage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
全选控件沿用表格的按需显示方式，补上可删除请求的行操作，批量连接测试并行发出。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 桌面全选在悬停、聚焦或选中时出现，触屏可操作。
- [ ] #2 符合删除条件的请求可单条确认删除，活动或待核实请求仍受后端保护。
- [ ] #3 勾选账号的连接测试并发进行，逐行报告进度与结果。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
调整共享复选框样式，接入现有请求删除 API 并处理末页回退，复用逐行反馈并行测试。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
65 项相关后端测试和前端构建通过。Playwright 用隔离模拟数据验证队列和账号表头复选框的隐藏、悬停、聚焦及选中状态；确认活动请求无删除入口、单条删除需要确认，最后一页删空后回退。两个所选账号的请求在任一个返回前均已发出，成功和失败分别显示在对应行。未删除实际请求记录。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
全选控件按需显示，请求列表支持安全的单条删除，账号批量连接测试并发执行。
<!-- SECTION:FINAL_SUMMARY:END -->
