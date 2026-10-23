---
id: TASK-4
title: 恢复管理台新增账号能力
status: 待验收
assignee: []
created_date: '2026-10-23T15:00:00Z'
updated_date: '2026-10-23T15:13:00Z'
labels:
  - migration
  - historical-evidence
milestone: m-0
dependencies: []
references:
  - src/ecmwf_downloader/interfaces/http/app.py
  - tests/test_new/test_api.py
documentation:
  - doc/note/acceptance_2026-10-07.md
priority: medium
type: bug
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
原 POST /api/v1/accounts 因 DTO id 与应用服务 account_id 不匹配返回 500；已修复并留有 2026-10-07 的 API 与浏览器证据。用户于 2026-10-23 明确要求提交，修复和回归测试已保存为独立提交 f233e7f。任务仍待用户验收，提交不代表验收通过。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 省略 ID 可生成账号 ID，显式 ID 可保留
- [ ] #2 新增和账号列表公共响应不泄露虚构 API Key
- [ ] #3 定向账号 API 回归结果及变更原因有记录
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-23：按用户要求提交 f233e7f，代码自历史验证后未再改动，本次差异检查通过。未改变待验收状态或勾选验收项。
<!-- SECTION:NOTES:END -->
