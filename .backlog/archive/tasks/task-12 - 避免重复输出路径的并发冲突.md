---
id: TASK-12
title: 避免重复输出路径的并发冲突
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-27T16:32:00Z'
labels:
  - migration
  - superseded
milestone: m-1
dependencies: []
references:
  - src/ecmwf_downloader/application/request_builder.py
  - src/ecmwf_downloader/application/worker.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: high
type: bug
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
相同请求的默认文件名或显式同名输出可能共用 .part；现有文件检查后还存在重命名覆盖窗口，影响下载数据完整性。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 同路径并发任务不能删除或覆盖彼此临时输出
- [ ] #2 默认不覆盖语义在并发竞争下仍成立
- [ ] #3 覆盖重复请求和显式同名的定向回归并记录冲突行为
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-28 已批准的 DRAFT-7 取消本地文件输出与 .part，原输出路径冲突需求不再适用。本项按已取消需求归档，未设 Done、未勾选验收，也不宣称修复了旧下载器；新请求的租约和重复提交由 TASK-32/TASK-10/TASK-11 跟踪。
<!-- SECTION:NOTES:END -->
