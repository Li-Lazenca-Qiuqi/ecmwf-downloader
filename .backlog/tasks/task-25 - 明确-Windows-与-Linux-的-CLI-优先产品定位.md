---
id: TASK-25
title: 明确 Windows 与 Linux 的 CLI 优先产品定位
status: Done
assignee: []
created_date: '2026-10-25T14:18:00Z'
updated_date: '2026-10-25T16:01:00Z'
labels: []
dependencies: []
priority: medium
type: docs
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户明确产品同时面向 Windows 和 Linux，主要在命令行使用，后台后端通过本地 HTTP 端口提供管理台。Linux 服务器通过 SSH 端口转发访问，仅需回环监听。本轮修正产品说明和项目入口，整理 Windows 原生兼容及后台运行说明需求，不将目标平台误写为当前全部已验证，也不更改监听地址或启动新的实现工作。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Product、AGENTS 与 README 一致说明 Windows/Linux、CLI 优先、后台服务和 Web 管理台的定位
- [ ] #2 服务器通过 SSH 端口转发访问，生产环境后端同源提供 API 与前端，保持回环监听
- [ ] #3 区分 Linux/WSL 已验证与 Windows 原生兼容未完成，完整需求写入 Draft 供审查
- [ ] #4 仅验证文档和记录一致性，不变更运行服务、任务状态或数据，不自动提交
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 对照当前 CLI、HTTP、SecretStore 与平台说明。2. 按用户已确认的 SSH 转发方式更新 Product、AGENTS 和 README。3. 在 Drafts 保存跨平台及后台运行要求，记录 fcntl 文件锁等已知差距，需求审查前不拆实现任务。4. 检查平台措辞、链接、任务原状态与代码完整性，删除临时脚本后交待验收。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25：用户确认产品面向 Windows 和 Linux，以 CLI 为主要入口，后台服务通过本地端口提供管理台；服务器采用 SSH 端口转发，因此保留 127.0.0.1 监听。已通过 CLI 更新 Product，增加目标与当前验证边界矩阵，并创建 DRAFT-2 保存完整需求供用户审查。AGENTS 与 README 已同步，README 提供 Bash 和 PowerShell 的 SSH -L 回环转发示例，每个选项分行。现有生产架构由后端同源提供 API、SSE 和前端，不需单独部署 Vite。代码核对发现 SecretStore 的 fcntl 文件锁仍是原生 Windows 兼容缺口，不能将 WSL 当作 Windows 原生验收。文档 3 个本地链接、平台和 SSH 回环措辞及 git diff --check 通过；仅修正文档和需求记录，未修改应用代码、监听配置或任务数据，未运行产品测试、构建或视觉验证。临时脚本已删除，未提交 Git；实现任务待需求审查后再拆分，任务交由用户验收。
<!-- SECTION:NOTES:END -->
