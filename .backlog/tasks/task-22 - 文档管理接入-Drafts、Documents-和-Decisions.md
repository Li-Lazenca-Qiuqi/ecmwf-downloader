---
id: TASK-22
title: 文档管理接入 Drafts、Documents 和 Decisions
status: 待验收
assignee: []
created_date: '2026-10-25T08:18:00Z'
updated_date: '2026-10-25T09:34:00Z'
labels: []
dependencies: []
documentation:
  - .backlog/drafts/
  - .backlog/docs/
  - .backlog/decisions/
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
统一需求、产品说明、专题笔记与决策的管理入口，保留内容、编号和引用；仅更新文档及项目指南。旧文件清理须列清单取得用户确认。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 需求、产品说明、笔记和决策在对应 Backlog 分类中可读
- [ ] #2 指南与现行引用已同步，已有任务状态及验收勾选保持不变
- [ ] #3 旧文件清理已获得用户确认并完成
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
通过 CLI 迁移需求和文档；决策正文通过用户允许的本地 Dashboard 接口保存；同步项目指南与引用，核对完整性。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
已迁移并逐份核对 4 份需求、文档和决策；项目指南及现行引用已同步。原有任务状态、依赖与验收勾选保持不变。旧文件未删除，清理清单已准备，等待用户确认；因此本任务保留 In Progress，未勾选验收条件。

收尾更新（2026-10-25）：用户已明确批准清理旧文件。本项目 4 个清单内旧 Markdown 已移入系统回收站，空目录已清理；迁移记录仍可读取，记录 ID 和依赖检查通过，删除后的入口与引用已同步。先前等待清理确认的事项已执行，验收勾选及完成状态交由用户设置。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
已统一 Drafts、Documents 和 Decisions 的管理入口，保留原有内容、编号及验证证据；相关指南与引用已同步，批准的 4 个旧文件已回收。正文、CLI 读取、记录 ID 和依赖检查通过；未自动提交 Git 或代用户验收。
<!-- SECTION:FINAL_SUMMARY:END -->
