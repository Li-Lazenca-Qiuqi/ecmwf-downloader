---
id: TASK-14
title: 验证异常与日志不会泄露凭据
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
  - src/ecmwf_downloader/interfaces/http/app.py
  - src/ecmwf_downloader/application/worker.py
  - src/ecmwf_downloader/infrastructure/cds.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: high
type: task
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
正常账号 DTO 不含 key 不能证明异常路径安全；Provider 异常、请求校验错误、任务错误与账号 last_error 都可能携带凭据。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 用虚构凭据覆盖 API 校验及客户端异常路径
- [ ] #2 公共错误、任务错误、账号错误及日志均不包含 key/token
- [ ] #3 定向回归与凭据保护说明同步
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
检查输入校验、配置存储和 CDS/AI 客户端的异常边界。用虚构凭据验证公共响应、任务事件、账号错误与日志。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
使用虚构 CDS Key、上游 Token 与 AI Key，验证无效配置、账号及 AI 校验、CDS 认证/字段/提交/轮询异常、旧账号错误、任务事件与 DEBUG 日志。异常响应只保留安全提示，服务地址拒绝 URL 凭据，CLI 设置和 HTTP DTO 只展示非敏感 AI 字段。验证损坏的凭据 YAML 不回显内容。93 项相关后端检查通过，测试使用隔离存储和模拟客户端。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
凭据输入、配置和客户端异常已做定向回归，公共响应、任务/账号错误、事件与日志未发现测试 Key 或 Token。
<!-- SECTION:FINAL_SUMMARY:END -->
