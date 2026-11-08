---
id: TASK-35
title: 支持 CDS 账号批量测试与逐行反馈
status: 待验收
assignee:
  - '@Codex'
created_date: '2026-11-08T13:46:00Z'
updated_date: '2026-11-08T13:49:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/AccountsPage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
账号页需要对所选账号批量测试连接，并在每个账号对应行显示认证反馈。删除仍只在单账号编辑中提供。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 表头可以全选，逐行可以勾选，批量测试仅针对已选账号。
- [ ] #2 单个和批量测试的进度与结果均归属对应账号，部分失败不影响其余账号测试。
- [ ] #3 删除仍通过单账号编辑弹窗执行。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用账号单条测试接口，依次执行所选账号并按 ID 保存进度和结果。复用队列复选框样式，使用模拟结果验证全选、部分选择和错误反馈。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TypeScript/Vite 构建通过。在现有 8000 实例上通过 Edge Playwright 的 1280px 和 375px 功能检查。模拟三个账号，验证表头全选与半选、批量仅发送两条已选账号请求、HTTP 失败后继续下一个、进度及成功/失败逐行显示、单条重试、单账号删除确认与选择清理。全部账号接口用浏览器替身，未访问真实 CDS 或改动真实账号。内置浏览器缺少运行组件，沿用已授权的 Playwright。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
账号列表支持逐行勾选、表头全选和批量连接测试。认证反馈在对应行，删除在单账号编辑中确认。功能验证通过，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
