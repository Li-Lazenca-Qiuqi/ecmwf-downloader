---
id: TASK-19
title: 使通用请求编辑与 Schema 回退可辨识
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T08:19:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - src/ecmwf_downloader/application/datasets.py
  - src/ecmwf_downloader/infrastructure/datastores.py
  - frontend/src/App.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: enhancement
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
在线 Schema 失败会静默回退到固定气象字段，离线表单不能完整表达 area 等 payload，constraints 未有效使用；不能据此宣称通用数据集验证。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 在线与离线回退来源清晰且失败状态可见
- [ ] #2 完整 payload 可编辑，保留字段类型和 area 等参数
- [ ] #3 constraints 按确认需求参与请求编辑且不伪造远端校验
- [ ] #4 用明确请求做定向验证并同步支持边界
<!-- AC:END -->
