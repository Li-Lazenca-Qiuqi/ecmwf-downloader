---
id: TASK-15
title: 让仅创建任务保存为待入队任务
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
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
当前管理台仅创建任务按钮调用预览接口，用户看见成功预览但并未产生任务；需要与 CLI/API 的创建语义一致。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 仅创建任务保存 pending 任务且不会自动入队
- [ ] #2 创建失败提供可见错误，不伪装成功
- [ ] #3 明确本地预览与 CDS 远端校验的区别并做定向功能验证
<!-- AC:END -->
