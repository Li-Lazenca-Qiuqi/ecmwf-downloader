---
id: TASK-18
title: 显示真实的服务状态与下载配置
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T15:51:00Z'
labels:
  - migration
  - merged
milestone: m-2
dependencies: []
references:
  - frontend/src/App.tsx
  - frontend/src/lib/api.ts
  - src/ecmwf_downloader/interfaces/http/app.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-17 已移除固定健康栏；服务使用实际 summary 请求结果，内置调度器和并发取运行时值，目录/重试/AI 启用从 settings 读取；无内置 Worker 有提示。隔离浏览器验证设置与 API 一致，本机实例重启后验证调度器运行。独立 Worker 与内置调度器状态有明确区分；本任务留待用户复核。

按用户本轮任务列表整理要求，本任务的真实状态与配置验收完整转入 TASK-17，旧固定健康栏已移除，不再作为独立实现任务。此次归档表示重复范围被合并，不表示用户验收通过。
<!-- SECTION:NOTES:END -->
