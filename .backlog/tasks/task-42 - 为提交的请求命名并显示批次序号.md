---
id: TASK-42
title: 为提交的请求命名并显示批次序号
status: 待验收
assignee:
  - '@codex'
created_date: '2026-11-09T15:36:00Z'
updated_date: '2026-11-09T15:52:00Z'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 需求

一次提交生成多条请求时，队列应能看出它们属于同一批，以及每条是第几份。

## 验收条件

- 提交页可以输入请求名称，留空用数据集名称。一次提交的子请求共享这个名称。
- 队列按计划顺序显示固定的 1/3、2/3、3/3；翻页、筛选、删除单条或重新提交某条都不重新编号。未拆分的请求只显示名称。
- CDS 时间拆分和一次选多个 NCAR 文件都支持。旧记录保留原名和现有详情。
- SQLite 单独保存批次元数据，批次与子请求一并写入。已有请求表和历史记录继续可读。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 提交页可填名称，留空使用数据集名称，单份只显示名称。
- [ ] #2 多份 CDS 与 NCAR 请求按计划显示固定序号，分页、筛选、删除、重新提交和重启保持原序号。
- [ ] #3 批次数据独立保存并与请求原子写入，旧记录和原名称可继续读取。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 通过启动建表创建独立批次成员表，在同一事务保存名称、批次 ID、原份数、计划序号和请求。
2. API 创建支持名称，保留原计划标题，列表按名称搜索。提交页名称只进入创建请求，队列及详情显示批次名称和序号。
3. 定向验证旧库打开、批次回滚、跨页和重试后的序号、NCAR、多份与单份前端交互。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
65 项队列、SQLite、REST、编辑器与镜像相关回归通过。新增两项定向用例通过，覆盖旧表直接打开、固定份次、分页搜索、删除、重试和重启，以及 NCAR 第二份写入失败后的整批回滚。前端构建和模拟浏览器提交通过。已更新 8000 实例，实际核对原库 3 条记录的 ID 和标题及调度器状态。未向源站发送验收请求。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
提交可命名，拆分后按固定份次显示。批次成员元数据独立存储并与请求一并提交，旧记录沿用原标题。相关验证通过，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
