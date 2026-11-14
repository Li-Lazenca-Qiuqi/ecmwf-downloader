---
id: TASK-37
title: 完善列表全选、请求删除和并发连接测试
status: Done
assignee:
  - '@Codex'
created_date: '2026-11-09T11:13:00Z'
updated_date: '2026-11-11T06:54:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/QueuePage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
全选控件沿用表格的按需显示方式，补上可删除请求的行操作，批量连接测试并行发出。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 桌面全选在悬停、聚焦或选中时出现，触屏可操作。
- [ ] #2 符合删除条件的请求可单条确认删除，活动或待核实请求仍受后端保护。
- [ ] #3 勾选账号的连接测试并发进行，逐行报告进度与结果。
- [ ] #4 刷新前后队列行高稳定，行内和批量操作共用状态条件，批量删除只处理所选可删除记录并确认。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
调整共享复选框样式，接入现有请求删除 API 并处理末页回退，复用逐行反馈并行测试。

精简请求操作列，去掉独立详情按钮，重新提交使用圆形箭头并保留操作提示。

固定状态说明占位；批量和单条共用刷新、复制、重试、取消及删除的条件和请求执行路径。可监视远端任务提前查询，核实提交逐条处理。定向验证行高、混合选择、删除部分失败和查询调度。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
65 项相关后端测试和前端构建通过。Playwright 用隔离模拟数据验证队列和账号表头复选框的隐藏、悬停、聚焦及选中状态；确认活动请求无删除入口、单条删除需要确认，最后一页删空后回退。两个所选账号的请求在任一个返回前均已发出，成功和失败分别显示在对应行。未删除实际请求记录。

操作列移除独立查看详情按钮，点击请求名称查看详情；重新提交改为带提示的圆形箭头，继续监视与核实提交仍可操作。前端构建通过，Edge Playwright 在 1200px 和 375px 用模拟请求确认详情、按钮与 retry 接口。

用户复验调整了队列批量操作。状态说明始终占一行。刷新、复制、重试、取消和删除共用状态条件，已绑定远端的活动请求可提前轮询。43 项定向测试及前端构建通过。1200px 与 375px 的浏览器模拟验证了刷新时文件大小消失而行高不变、单条刷新、混合选择、批量删除确认及部分失败后的保留选择。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
全选控件按需显示。队列单条与批量共用操作条件，删除须确认，刷新前后行高稳定。已通过定向验证，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
