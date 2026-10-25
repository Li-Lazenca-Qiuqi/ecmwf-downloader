---
id: TASK-10
title: 保证调度器关停和租约切换时写入安全
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T15:43:00Z'
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
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
已有记录指出 stop 不等待下载线程就释放调度器租约，失去租约时旧 Worker 仍可能写文件。需要保证单工作区所有权切换的正确性，避免不同 Worker 相互干扰。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 关停或失去所有权后旧 Worker 不再写任务输出
- [ ] #2 覆盖运行中关停、重启和租约转移的定向回归
- [ ] #3 文档明确安全关停与取消边界
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
本轮空队列切换本机实例时观察到旧进程在 SIGTERM 后未完全退出，SIGINT 后关闭；启动过早会因旧租约尚未过期导致新实例不消费。等待旧租约过期后重启已恢复。没有活动下载，不涉及真实文件；本次队列简化未扩展修复租约接管/重试启动问题。
<!-- SECTION:NOTES:END -->
