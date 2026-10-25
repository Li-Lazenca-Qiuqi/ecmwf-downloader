---
id: decision-1
title: 0001_local_cli_web
date: '2026-10-25T08:18:00Z'
status: recorded
---
## Context

本条保存已有决策及其依据，具体状态与适用边界见原文。

## Decision

<!-- source: doc/decisions/0001_local_cli_web.md -->

### 0001：本机 CLI + Web 架构

状态：现有决策整理。依据：0.5.0 代码、AGENTS、CHANGELOG 和提交 `5f25c98`（2026-08-17）。整理日期：2026-10-07。

#### 背景与决定

项目从 Textual TUI 转为本机单用户 Typer CLI 与 FastAPI/React 管理台。CLI 直接调用应用服务，Web 提供 REST/SSE，Worker 复用相同应用容器。请求保持通用的 `dataset_id + request_payload`。

SQLite WAL 存储任务、事件、调度租约、账号运行状态和模板。密钥独立存入 `0600` 的 YAML，使用文件锁及原子替换；不混入公共 DTO 或非敏感配置。下载写 `.part` 后原子重命名。

Python wheel 包含预构建前端，运行时不需要 Node。Web CLI 限制回环监听，不引入认证和多用户能力。

#### 代价与约束

Linux 文件锁是运行约束；Windows 环境通过 WSL 使用 Linux 工具链。数据库租约并不自动保证旧 Worker 不再写文件，现有不足必须由恢复与关停测试约束。

0.5.0 使用全新数据库，旧 YAML/JSON 任务历史不迁移；旧配置及下载文件不自动删除。首版只提供安全点取消，不承诺暂停或可靠断点续传。改变这些边界需另行确认需求。

## Consequences

约束、影响及后续事项见上方原始记录。
