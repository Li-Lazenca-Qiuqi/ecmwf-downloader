---
id: TASK-14
title: 验证异常与日志不会泄露凭据
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
labels:
  - migration
milestone: m-1
dependencies: []
references:
  - src/ecmwf_downloader/interfaces/http/app.py
  - src/ecmwf_downloader/application/worker.py
  - src/ecmwf_downloader/infrastructure/cds.py
documentation:
  - doc/PRODUCT.md
priority: high
type: task
ordinal: 14000
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
