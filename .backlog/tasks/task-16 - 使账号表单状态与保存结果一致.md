---
id: TASK-16
title: 使账号表单状态与保存结果一致
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T08:19:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/lib/api.ts
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: bug
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增账号的禁用选择未应用到新账号；切换编辑对象可能残留表单状态，保存和连接测试结果反馈也不完整。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 新建时选择禁用后账号保持 disabled
- [ ] #2 切换编辑账号时表单显示正确对象且凭据不外泄
- [ ] #3 保存与连接检查成败有可见反馈，定向测试及说明同步
<!-- AC:END -->
