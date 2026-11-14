---
id: TASK-11
title: 恢复启动后才过期的遗留任务
status: Done
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-11-08T12:49:00Z'
labels:
  - migration
milestone: m-1
dependencies: []
references:
  - src/ecmwf_downloader/application/worker.py
  - src/ecmwf_downloader/infrastructure/repositories.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: high
type: bug
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
已有恢复仅在启动执行；若旧任务租约当时仍有效，之后过期也可能一直 running，造成队列不能自行恢复。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 启动时未过期、运行中才过期的请求租约能恢复，有已知远端 ID 时继续查询
- [ ] #2 有效拥有者的租约不错误恢复，未知提交转待核实而不盲目自动重发
- [ ] #3 定向回归覆盖迟到过期、有效租约、已知 ID 和未知提交，记录恢复边界
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-28 新请求队列每轮扫描过期租约，不只启动时扫描；旧 worker_id 清除后，已知 ID 保持原账号与作业，未知提交进入 submission_unknown。有效租约、迟到过期、已知/未知 ID 定向检查通过；不扫描或清除旧科学数据文件。
<!-- SECTION:NOTES:END -->
