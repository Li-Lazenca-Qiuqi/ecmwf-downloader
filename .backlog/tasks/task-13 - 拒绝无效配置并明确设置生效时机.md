---
id: TASK-13
title: 拒绝无效配置并明确设置生效时机
status: Done
assignee:
  - '@Codex'
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-11-08T13:04:00Z'
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
ordinal: 28000
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
校验 CLI 与 API 的配置更新，在同目录暂存并原子替换 app.yaml，防止并发更新丢失。区分同进程 PATCH 和独立 CLI 修改的生效时机，用故障注入及重新启动验证。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25 当前简化设置页已经明确并发和轮询等调度器参数重启后生效；本任务不要求补做完整热更新。仍需修复 CLI/API 更新先落盘后校验和保存失败保护，故保留活动待办。

2026-10-28 DRAFT-7 改用 requests 配置；新增严格类型、范围和退避列表验证，非法请求配置保存前拒绝，后续调度读取新参数。此子范围 7 类无效配置/持久化前拒绝已验证。非敏感配置写入失败的原子性等原任务要求仍未补齐，因此保留 To Do，不冒称整体完成。

应用配置在同目录暂存、同步并原子替换，并发写入合并最新磁盘值；运行进程仅应用本次 PATCH。独立 CLI 保存后重启读取，已有请求保留自身重试上限，已安排的轮询或退避照常执行。93 项相关后端检查通过，其中包括无效 PATCH 后重新读取、应用配置与凭据各自替换失败时保留原文件和运行值、并发合并、CLI 与 API 生效时机。应用配置与凭据文件分别原子替换，双文件保存的凭据错误会回退应用配置。设置页与产品文档已同步，未验收 Windows 原生。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
配置先验证再写盘，保存失败保留原值。通过定向故障注入、CLI 重启读取与同进程 PATCH 验证，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
