---
id: TASK-19
title: 明确 AI 与 CLI 的 Schema 和约束查询回退来源
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T15:51:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - src/ecmwf_downloader/application/datasets.py
  - src/ecmwf_downloader/infrastructure/datastores.py
  - src/ecmwf_downloader/interfaces/cli/app.py
  - frontend/src/pages/RequestPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: enhancement
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
当前管理台以 JSON 编辑完整请求，旧固定字段表单与 constraints 驱动字段联动不再属于已确认的单一队列简化路线。完整 payload 和类型保真交由 TASK-17 验收。本任务仅保留仍存在于 DatasetService 的静默 Schema/constraints 回退：这些结果仍供可选 AI 建议、CLI 与 API 使用，不能把固定回退字段或空约束描述为 CDS 在线验证。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Schema 与 constraints 查询能区分在线结果、回退、未查询及失败，说明来源和有效边界
- [ ] #2 可选 AI 使用回退 Schema 时有可辨识提示，建议仍需审核，不作为远端可下载证明
- [ ] #3 本地 JSON/预览不声称完成 CDS 远端约束验证；不再要求 constraints 驱动动态表单联动
- [ ] #4 对在线成功、缺少账号和查询失败做定向验证，文档同步，不使用真实凭据
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 根据新技术路线缩小范围：撤销旧字段表单补齐和约束联动要求；JSON 编辑由 TASK-17 承接。源码核对仍有 except 后静默返回固定 fields / 空 constraints，且 AI 和 CLI/API 仍使用该查询，因此本任务保留 To Do，不能因移除表单就判定问题消失。
<!-- SECTION:NOTES:END -->
