---
id: TASK-11
title: 恢复启动后才过期的遗留任务
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
labels:
  - migration
milestone: m-1
dependencies: []
references:
  - src/ecmwf_downloader/application/worker.py
  - src/ecmwf_downloader/infrastructure/repositories.py
documentation:
  - doc/PRODUCT.md
priority: high
type: bug
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
已有恢复仅在启动执行；若旧任务租约当时仍有效，之后过期也可能一直 running，造成队列不能自行恢复。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 启动时尚未过期、稍后过期的遗留任务能恢复调度
- [ ] #2 有有效拥有者的任务不被错误恢复
- [ ] #3 定向回归覆盖恢复窗口并更新限制说明
<!-- AC:END -->
