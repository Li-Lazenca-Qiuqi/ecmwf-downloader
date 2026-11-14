---
id: TASK-41
title: 重做队列请求详情与参数视图
status: Done
assignee:
  - '@Codex'
created_date: '2026-11-09T14:26:00Z'
updated_date: '2026-11-11T07:04:00Z'
labels: []
dependencies: []
references:
  - frontend/src/pages/QueuePage.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
队列详情按请求概况、结果链接和参数分区。请求参数提供与提交页一致的卡片和 JSON 视图。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 请求详情以卡片视图打开，可切换 JSON 查看同一份已保存参数。
- [ ] #2 详情保留结果复制和待核实请求的关联操作，窄屏可滚动并关闭。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用提交页卡片与 JSON 组件，从已存请求读取参数，按设计预览组织详情。定向验证队列和提交页的视图切换。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
前端 npm run build 通过。通过本地实例和模拟接口，在 1200px 与 375px 验证队列详情默认卡片、JSON 与保存参数一致、链接复制、Esc 关闭并恢复焦点、待核实请求关联，以及提交页的卡片和 JSON 切换。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
队列详情分为请求概况、结果链接和参数。队列与提交页共用卡片和 JSON 组件，队列展示记录中保存的请求参数。功能验证通过，交由用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
