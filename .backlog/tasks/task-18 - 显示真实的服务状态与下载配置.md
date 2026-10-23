---
id: TASK-18
title: 显示真实的服务状态与下载配置
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/lib/api.ts
  - src/ecmwf_downloader/interfaces/http/app.py
documentation:
  - doc/PRODUCT.md
priority: medium
type: bug
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
管理台的服务、调度器、数据库健康与部分并发/目录/重试字段为固定文案，在 --no-worker 等状态下可能误导用户。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 服务和调度器状态来源于实际运行状态
- [ ] #2 并发、输出目录与重试信息与当前设置一致
- [ ] #3 异常或未检查状态不会显示为固定健康，定向验证与文档同步
<!-- AC:END -->
