---
id: TASK-13
title: 拒绝无效配置并明确设置生效时机
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T15:51:00Z'
labels:
  - migration
milestone: m-1
dependencies: []
references:
  - src/ecmwf_downloader/application/container.py
  - src/ecmwf_downloader/config.py
  - src/ecmwf_downloader/application/worker.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: high
type: bug
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
现有设置先落盘后校验，无效 max_workers 可能影响下次启动；已有 Scheduler 保存的并发和轮询参数也没有完整热更新语义。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 无效设置更新不改变已有有效配置
- [ ] #2 有效设置可靠保存，保存失败不损坏原配置
- [ ] #3 并发和轮询设置的生效时机明确且与实际行为一致
- [ ] #4 定向回归覆盖无效 PATCH 与后续启动，文档同步
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 当前简化设置页已经明确并发和轮询等调度器参数重启后生效；本任务不要求补做完整热更新。仍需修复 CLI/API 更新先落盘后校验和保存失败保护，故保留活动待办。
<!-- SECTION:NOTES:END -->
