---
id: TASK-21
title: 修复窄屏布局并保留交互回归覆盖
status: To Do
assignee: []
created_date: '2026-10-23T15:02:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/styles.css
  - doc/note/acceptance_2026-10-07.md
documentation:
  - doc/PRODUCT.md
priority: medium
type: bug
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
历史 390px 检查发现默认导航遮挡，收起后顶部按钮和工具栏仍横向溢出。任务保留需求与证据；按新规则，不在普通任务中主动启动视觉验证。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 窄屏导航可收起且主要操作可达
- [ ] #2 顶部与工具栏不引起页面横向溢出，表格只在容器内滚动
- [ ] #3 只对明确功能做定向回归；视觉验证需明确需求，并记录错误反馈、SSE 与取消相关功能覆盖
<!-- AC:END -->
