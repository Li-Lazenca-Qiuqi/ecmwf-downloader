---
id: TASK-9
title: 完成真实 CDS 小请求下载与内容验收
status: To Do
assignee: []
created_date: '2026-10-23T15:00:00Z'
labels:
  - migration
  - blocked
  - live-cds
milestone: m-0
dependencies: []
references:
  - doc/note/cds_smoke_request.yaml
  - doc/PRD/0.5.0_acceptance.md
documentation:
  - doc/PRODUCT.md
priority: high
type: task
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
0.5.0 尚无真实下载通过证据。2026-10-07 检查时账号为空；本轮未检查最新凭据状态。用户已选择 2m temperature、2024-01-01 00:00 UTC、31/120/30/121 degree 的 NetCDF 小请求。不得在聊天或文档索要/记录密钥。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 通过项目 Worker 完成已选小请求，并记录实际日期与结果
- [ ] #2 任务为 completed，输出可读且 .part 已消失
- [ ] #3 核对 variable、UTC 时间、经纬度、单位、缺失值并保存证据
- [ ] #4 使用独立验收目录并保留真实下载数据
<!-- AC:END -->
