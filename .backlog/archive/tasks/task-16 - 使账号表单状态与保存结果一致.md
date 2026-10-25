---
id: TASK-16
title: 使账号表单状态与保存结果一致
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T15:51:00Z'
labels:
  - migration
  - merged
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
用户批准整体界面简化后，TASK-17 已移除新建时无效的禁用选择，新增默认可用、编辑支持禁用；表单按账号 ID 重新挂载，错误有反馈。隔离浏览器验证新增/编辑/禁用、密钥不回填及新建表单清空通过。旧验收项“新建时选择禁用”不再适用，保留待用户复核，不据此自动验收本任务。

按用户本轮任务列表整理要求，本独立任务并入 TASK-17 的账号验收范围。旧 AC1“新建时选择禁用”已随界面简化取消，新增统一默认可用；AC2/AC3 的表单、凭据及反馈要求已转入 TASK-17。此次归档表示重复范围被合并，不表示用户验收通过。
<!-- SECTION:NOTES:END -->
