---
id: TASK-44
title: 提交 CDS 请求时选择账号
status: Done
assignee:
  - '@codex'
created_date: '2026-11-11T07:08:00Z'
updated_date: '2026-11-11T10:37:00Z'
labels: []
dependencies: []
documentation:
  - doc-1
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
提交页增加一个紧凑的「提交账号」控件。单份默认选择今日使用次数最少的可用账号，多份支持多选。NCAR 文件请求无需 CDS 账号。

默认按今日使用次数排序，多份选用最多与份数相同的可用账号。按请求份次轮流分配给所选账号，份数超过账号数时循环。同一账号可承担多份。

分配在批次创建时随请求一并保存，独立记录指定账号。调度只用选定账号提交，指定账号暂不可用时排队。既有请求、CLI 和未传账号的 API 继续用原有自动调度。

验收时检查默认排序、单选和多选、分配与重启恢复，界面只保留字段标签和必要错误提示。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 单份默认选今日使用次数最少的可用 CDS 账号，多份默认多选且可调整。
- [ ] #2 按份次轮流分配，所选账号独立持久化，禁用时排队，重启保留。
- [ ] #3 CDS 拆分与 NCAR 多文件能创建完整批次，界面只保留控件和必要提示。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
用独立任务账号关联保存指定账号，在批次事务一并写入。调度领取时只用指定账号，自动任务延续旧策略。提交页使用紧凑的单选和多选控件，核对多份预览与提交并精简说明。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
旧版 CDS 两份拆分和 NCAR 两文件样例都能预览并发出创建请求，原始提交失败未复现。新版移除有效多份计划对后台约束查询完成的等待，继续拦截已知的 CDS 约束冲突。

相关 pytest 68 项通过，覆盖创建整批、账号轮流分配、停用等待、重启恢复。生产前端构建通过。新版 8000 实例使用在线 CDS 字段和 NCAR 目录验证预览，浏览器验证单选、多选、CDS 三份和 NCAR 两文件提交动作。浏览器拦截创建，后端用临时数据库与模拟提供方验证，未发送真实远端提交。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
提交页增加精简账号选择，按今日使用次数默认选择，按份次轮流分配并随批次保存。NCAR 文件请求可直接提交。
<!-- SECTION:FINAL_SUMMARY:END -->
