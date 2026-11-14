---
id: TASK-40
title: 统一管理台页面内容宽度
status: Done
assignee:
  - '@Codex'
created_date: '2026-11-09T12:07:00Z'
updated_date: '2026-11-11T06:55:00Z'
labels: []
dependencies: []
references:
  - frontend/src/styles.css
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
请求队列、提交请求、账号和设置使用统一的居中内容宽度，宽屏封顶，窄屏按比例收缩。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 四个页面和顶部导航内容使用同一宽度公式，内容最多 1360px，窄屏使用可用视口的 94%。
- [ ] #2 不同尺寸下内容不引入页面级横向滚动，已有表格仍在自身容器滚动。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
用共享 CSS 宽度变量替代各页独立上限，导航使用同一宽度对齐；在宽屏、过渡宽度和手机视口验证四页边界。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TypeScript/Vite 构建通过。Edge Playwright 在 320、375、850、851、1024、1440、1447、1920px 八种视口用模拟 API 验证四页共用 min(94%, 1360px)、水平居中、导航两侧对齐。保留滚动条空间时按可用宽度计算，未发生页面级横向溢出，窄屏账号表可在自身容器滚动。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
四页和导航内容统一按可用视口的 94% 伸缩，最大 1360px。八种视口的功能检查通过，交用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
