---
id: TASK-10
title: 保证调度器关停和租约切换时写入安全
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
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
已有记录指出 stop 不等待下载线程就释放调度器租约，失去租约时旧 Worker 仍可能写文件。需要保证单工作区所有权切换的正确性，避免不同 Worker 相互干扰。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 关停或失去租约后不再领取新请求，已发操作的远端 ID/状态可安全保存，不产生重复提交
- [ ] #2 关停等待在途提交并续租、保存 ID 后释放；接管拥有者通过同一事务校验租约后才能领取
- [ ] #3 覆盖关停、重启、旧拥有者领取被拒绝的定向回归，文档明确不明确提交与取消边界
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
本轮空队列切换本机实例时观察到旧进程在 SIGTERM 后未完全退出，SIGINT 后关闭；启动过早会因旧租约尚未过期导致新实例不消费。等待旧租约过期后重启已恢复。没有活动下载，不涉及真实文件；本次队列简化未扩展修复租约接管/重试启动问题。

2026-10-28 按 DRAFT-7 改为请求监视安全。领取在 SQLite 写事务内核对全局租约拥有者与过期时间；关停等待 Future 保存远端 ID 并持续续租后释放。已通过在途提交关停、旧/新 owner fencing、并发领取与租约争用测试；真实服务重启后更新同一 CDS 作业链接。没有本地文件输出，旧输出写入条款取消。
<!-- SECTION:NOTES:END -->
