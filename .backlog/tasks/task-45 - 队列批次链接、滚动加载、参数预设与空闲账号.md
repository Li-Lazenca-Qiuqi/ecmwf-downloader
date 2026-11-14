---
id: TASK-45
title: 支持 Windows 原生凭据锁与运行验证
status: Done
assignee:
  - '@codex'
created_date: '2026-11-11T10:46:00Z'
updated_date: '2026-11-14T03:01:00Z'
labels: []
dependencies: []
documentation:
  - doc-1
priority: high
type: bug
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
源自 DRAFT-8 的平台优先级及 DRAFT-2。Windows 原生为主要使用环境，Linux 继续支持。现有凭据读写直接使用 fcntl，需要覆盖原生 Windows 的跨进程访问。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 凭据读写复用跨平台文件锁，Web 和 CLI 并发修改不同凭据时均能保存。保留原子替换，Linux 保持现有权限保护。
- [ ] #2 用独立配置在原生 Windows 验证 CLI 启动、账号保存、Web 启停，以及重启后继续监视已有请求。分别记录原生 Windows 和 Linux/WSL 的相关回归结果。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用通用文件锁保护凭据初始化、读写和原子替换。用 Windows 原生隔离环境和 Linux 回归验证。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Windows 原生 Python 3.12 隔离环境实际运行 CLI 和 Web，两个进程并发添加不同账号均保留。使用控制台信号正常关停后重新启动，继续查询同一模拟远端 ID 并取得链接，远端模拟提交只发生一次。WSL 定向回归通过。

本地独立 Windows 原生验收实例使用 Python 3.12.11，CLI 初始化及 Web 健康检查通过。应用户要求关闭 8001 验收实例。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
凭据初始化、读取和更新复用跨平台锁。
<!-- SECTION:FINAL_SUMMARY:END -->
