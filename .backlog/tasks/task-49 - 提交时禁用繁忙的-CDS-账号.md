---
id: TASK-49
title: 提交时禁用繁忙的 CDS 账号
status: Done
assignee:
  - '@codex'
created_date: '2026-11-11T11:53:00Z'
updated_date: '2026-11-14T02:59:00Z'
labels: []
dependencies: []
documentation:
  - doc-1
priority: medium
type: enhancement
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
源自 DRAFT-8，沿用 TASK-36 的后端繁忙状态和 TASK-44 的显式账号分配。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 单选和多选均显示繁忙状态并禁用对应选项，默认从空闲且可用的账号里按今日使用次数选择。
- [ ] #2 后端提交时复核所选账号，选定后变繁忙时清楚提示重新选择或等待。没有空闲账号时显示简短提示。
- [ ] #3 已提交请求保留固定账号分配，所选账号少于请求份数时仍按原规则轮流分配。NCAR 提交无需选择 CDS 账号。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
在提交页禁用繁忙账号，创建批次时在同一写事务复核繁忙状态，保留既有份次分配。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Playwright 验证空闲默认选中、繁忙账号单选及多选均禁用。API 验证账号在提交前被调度领取变忙时拒绝整批，既有分配测试通过。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
单选与多选都禁用繁忙账号，后端创建时再次检查。
<!-- SECTION:FINAL_SUMMARY:END -->
