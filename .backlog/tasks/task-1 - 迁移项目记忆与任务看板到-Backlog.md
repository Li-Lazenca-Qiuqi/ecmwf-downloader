---
id: TASK-1
title: 迁移项目记忆与任务看板到 Backlog
status: Done
assignee: []
created_date: '2026-10-23T14:57:00Z'
updated_date: '2026-10-25T12:38:00Z'
labels:
  - migration
milestone: m-0
dependencies: []
priority: high
type: docs
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 2026-10-23 用户新规则替换 TODO/Roadmap 的活动入口，保留已有实现、历史验证与外部阻塞的证据，避免把已实现等同于用户验收。只整理项目记忆与看板，不扩展功能开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 项目使用 .backlog/config.yml，Git 集成启用，auto_commit=false，包含待验收状态
- [ ] #2 旧清单与阶段规划完整迁入看板及里程碑，历史通过项保留日期且未标记 Done
- [ ] #3 旧 TODO/Roadmap 入口、历史快照及重复迁移文件已删除，AGENTS 和有效文档链接指向 Backlog
- [ ] #4 可再生成的测试与构建中间产物已清理，已有代码、配置、下载数据和正式产物保持完整
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 按用户明确授权列出并删除旧 TODO/Roadmap 的入口、快照和重复迁移汇总。2. 清理可再生成的测试缓存、覆盖率和构建元数据，不创建备份。3. 更新 AGENTS、PRODUCT、PRD 和验收记录链接，将迁移事实统一留在 Backlog。4. 核对任务、代码、数据与发布产物保持完整，验证链接和差异后交待验收。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-23：按用户最新要求直接删除 5 个旧文档：TODO/Roadmap 弃用入口、两份历史快照、重复迁移汇总；清理 263 个可再生成的缓存和中间文件，以及 15 个遗留空目录。未备份。AGENTS、PRODUCT、验收记录与 archive 说明已同步，现存 3 个文档链接检查通过。既有代码内容摘要以及配置、数据、发布产物的元数据核对一致；21 项任务和 3 个里程碑保留，验收项全部未勾选。git diff --check 通过。未重跑测试、构建、下载或视觉验证，未提交 Git。后续由 AGENTS 和本任务恢复当前工作，不再维护平行迁移记录；交由用户验收，不代设 Done。

2026-10-23 后续：用户明确要求 Git 提交。账号修复及回归测试已独立提交 f233e7f；项目记忆、Backlog 和有效文档作为另一独立工作单元提交。本次配置、21 项任务状态、62 项未勾选验收标准、3 个有效文档链接及引用检查通过。此前未提交的说明为该阶段记录，不影响本次提交授权；所有任务继续等待用户验收。
<!-- SECTION:NOTES:END -->
