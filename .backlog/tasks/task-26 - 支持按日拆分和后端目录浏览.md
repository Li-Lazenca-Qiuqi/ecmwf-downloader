---
id: TASK-26
title: 支持按年、月、日拆分请求
status: Done
assignee: []
created_date: '2026-10-26T05:58:00Z'
updated_date: '2026-11-08T09:16:00Z'
labels: []
dependencies: []
documentation:
  - .backlog/drafts/draft-4 - 添加任务字段选择、实时预览与年月日拆分.md
type: feature
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
保留 DRAFT-4 中的年月日拆分能力。按 DRAFT-7 将日期拆分用于远端请求，预览与创建复用同一套日历规则。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 年/月/日拆分处理闰年、大小月、无效日期和缺失维度，预览明确提示过滤日期
- [ ] #2 API/CLI 与创建预览语义一致，定向回归通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 增加 day 策略和统一拆分结果及警告；2. 增加只读目录应用服务和 HTTP 接口；3. 隔离目录测试日期边界、目录权限与 API/CLI。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26 已完成 DRAFT-4 实施：完整在线字段、来源/缓存/错误说明；选择式控件与顶部 AI、实时只读预览；后端目录浏览；year/month/day 拆分及日历警告。34 项相关后端测试、TypeScript/Vite 构建和隔离 Playwright 功能检查通过，含搜索/批选、类型、目录、AI 过期/无效防护及创建 queued。真实只读核对 ERA5 single levels 为 12 字段/262 变量、ERA5-Land 月平均为 11 字段/60 变量且无日字段；本机 API 已验证。没有真实下载、外部 AI 调用、视觉或 Windows 原生验收。用户数据与账号页既有改动保留，未提交，验收项未勾选。

2026-10-28 DRAFT-7 已获用户确认并实施于 TASK-32：软件不再本地下载，移除输出目录/浏览/覆盖/传输进度及旧 enqueue/run 入口；保留自动提交、字段、AI、预览和请求日期拆分。原用户完成状态与验收记录不改写，冲突旧条款不作为当前验收要求。
<!-- SECTION:NOTES:END -->
