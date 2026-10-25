---
id: TASK-7
title: 验证本地 HTTP 任务流转与 SSE 重连
status: 待验收
assignee: []
created_date: '2026-10-23T15:00:00Z'
updated_date: '2026-10-25T08:19:00Z'
labels:
  - migration
  - historical-evidence
milestone: m-0
dependencies: []
references:
  - .backlog/docs/notes/doc-2 - acceptance_2026-10-07.md
documentation:
  - .backlog/docs/notes/doc-2 - acceptance_2026-10-07.md
priority: medium
type: task
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-10-07 在独立数据库和配置下，真实本地 HTTP 验证预览、pending 到 queued 到 cancelled，并验证 Last-Event-ID 重连；未向 CDS 下载。

迁移规则：旧清单的勾选只代表历史实现或验证，2026-10-23 未重验，不代替用户验收；验收清单保持未勾选。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 本地任务流转和 SSE 事件恢复结果可追溯
- [ ] #2 记录明确区分本地 HTTP 与真实 CDS 下载
<!-- AC:END -->
