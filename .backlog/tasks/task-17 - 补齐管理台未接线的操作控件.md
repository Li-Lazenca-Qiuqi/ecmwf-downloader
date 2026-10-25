---
id: TASK-17
title: 补齐管理台未接线的操作控件
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
  - .backlog/docs/product/doc-1 - Product.md
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: enhancement
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
任务筛选、分页、批量、详情、模板、重置以及账号搜索与规则控件有展示未接线情况，易让用户误判功能可用。后续实施前需确认各控件范围，可按实际需求细分任务。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 按确认的范围逐项接入或明确禁用未完成控件
- [ ] #2 控件行为与 CLI/API 实际能力一致
- [ ] #3 针对确认功能测试并更新 PRODUCT 支持范围
<!-- AC:END -->
