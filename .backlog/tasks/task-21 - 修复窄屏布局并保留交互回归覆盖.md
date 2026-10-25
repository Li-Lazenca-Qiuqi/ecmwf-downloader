---
id: TASK-21
title: 验证简化界面的窄屏操作与滚动边界
status: To Do
assignee: []
created_date: '2026-10-23T15:02:00Z'
updated_date: '2026-10-25T15:51:00Z'
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
ordinal: 21000
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 旧侧栏修复要求取消，改为验证当前顶部导航与滚动边界；TASK-17 的窄屏导航结果仅覆盖功能可达，不自动替代视觉或完整布局验收。状态仍为 To Do。
<!-- SECTION:NOTES:END -->
