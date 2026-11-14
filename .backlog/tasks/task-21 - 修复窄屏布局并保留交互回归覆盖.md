---
id: TASK-21
title: 验证简化界面的窄屏操作与滚动边界
status: Done
assignee:
  - '@Codex'
created_date: '2026-10-23T15:02:00Z'
updated_date: '2026-11-08T13:04:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/styles.css
  - .backlog/docs/notes/doc-2 - acceptance_2026-10-07.md
  - frontend/src/pages/QueuePage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: task
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
旧 390px 证据对应已移除的侧栏、顶部按钮和双栏布局，不能继续作为新版仍有相同缺陷的结论。当前为顶部四入口导航和单队列，TASK-17 已做 375px 导航操作验证，但没有进行新版视觉检查或完整滚动边界验收。本任务保留现有界面在窄屏下的主要操作、滚动和定向交互回归；不再要求旧侧栏收起。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 顶部四入口导航和添加、取消等主要操作在窄屏可达，不要求已移除的侧栏收起功能
- [ ] #2 顶部与工具栏不引起页面横向溢出，表格只在容器内滚动
- [ ] #3 只对明确功能做定向回归；视觉验证需明确需求，并记录错误反馈、SSE 与取消相关功能覆盖
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
以 375px、390px 验证四入口、提交、取消、错误反馈、SSE 更新、页面与表格滚动；用隔离数据和模拟远端服务，修复实际复现的布局问题。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 旧侧栏修复要求取消，改为验证当前顶部导航与滚动边界；TASK-17 的窄屏导航结果仅覆盖功能可达，不自动替代视觉或完整布局验收。状态仍为 To Do。

用 Edge Playwright 在隔离 WSL 实例以 375×667 和 390×667 触屏视口检查四个导航入口、账号表格容器横向滚动与编辑弹窗、队列搜索/筛选/翻页、滚动后提交和取消。对取消模拟一次 409，核对可见错误，重试走真实本地 API 并确认已取消。另由外部 API 新建请求，通过真实 EventSource 接收任务事件，队列在下次轮询前更新。两种宽度文档、顶部和工具栏均无横向溢出，无意外浏览器报错。内置浏览器缺少运行组件，使用已授权 Playwright 回退。数据集使用替身，取消为本地排队请求，未做视觉验收。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
375px 和 390px 的四入口、主要操作、滚动、错误反馈与 SSE 功能回归通过，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
