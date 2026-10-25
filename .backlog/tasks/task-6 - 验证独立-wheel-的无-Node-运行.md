---
id: TASK-6
title: 验证独立 wheel 的无 Node 运行
status: Done
assignee: []
created_date: '2026-10-23T15:00:00Z'
updated_date: '2026-10-25T16:02:00Z'
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
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-10-07 将非 editable wheel 安装到独立环境，运行子进程 PATH 不含 Node；验证 CLI、Web、六个 SPA 路由和资源字节一致。

迁移规则：旧清单的勾选只代表历史实现或验证，2026-10-23 未重验，不代替用户验收；验收清单保持未勾选。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 独立安装 CLI 和 Web 的历史证据完整
- [ ] #2 六个 SPA 路由及静态资源验证有记录
- [ ] #3 明确构建时仍需要 Node
<!-- AC:END -->
