---
id: TASK-28
title: 接入官方完整数据集目录与名称搜索
status: 待验收
assignee: []
created_date: '2026-10-26T06:41:00Z'
updated_date: '2026-10-26T06:59:00Z'
labels: []
dependencies: []
type: feature
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户要求添加任务时可选择官方目录中的数据集，现有内置五项不能覆盖实际需求。需求已于 2026-10-26 明确批准，关联 DRAFT-4。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 完整跟随官方目录分页，展示数据集名称与 ID
- [ ] #2 按名称或 ID 搜索并选择后加载对应字段，保留手动输入 ID
- [ ] #3 明确展示在线、缓存和失败状态，不伪装完整目录
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
读取公开官方目录并完整分页，缓存结果；替换前端为可搜索选择器；定向测试分页、失败缓存、搜索和字段切换，并构建部署本地实例。

根据用户界面反馈，将刷新目录与获取字段合并为同一操作行；目录来源与数量拆成有层次的状态摘要。仅调整展示布局，定向构建检查。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
已实现完整官方目录分页、进程缓存一小时、显式失败/过期缓存，Web 名称和 ID 搜索、键盘选择、更多结果与手动 ID，CLI/API 支持搜索刷新。真实公开目录取得 145 项，monthly 搜索 25 项；26 项定向测试及 TS/Vite 构建通过。Playwright CLI 使用真实目录与模拟字段/约束验证搜索、选择、字段切换、展开、空结果、手动 ID、失败与缓存状态，无页面运行错误。实例 8000 已更新且 scheduler_running=true；未创建下载任务，无真实下载验收。用户验收条件保持未勾选。

根据用户反馈将刷新目录与获取字段放入同一 flex 操作组，获取字段设为主按钮；目录来源改为状态标签，数量单独显示并突出数值，支持窄屏换行但两个按钮保持同行。仅展示调整，TypeScript/Vite 构建和 git diff --check 通过，未新增无关测试或视觉验收。
<!-- SECTION:NOTES:END -->
