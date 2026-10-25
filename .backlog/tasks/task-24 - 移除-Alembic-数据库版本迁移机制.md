---
id: TASK-24
title: 移除 Alembic 数据库版本迁移机制
status: Done
assignee: []
created_date: '2026-10-25T13:53:00Z'
updated_date: '2026-10-25T14:00:00Z'
labels:
  - database
  - cleanup
dependencies: []
priority: medium
type: chore
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户明确认为当前产品数据库变化较少，不需要保留 Alembic Migration。项目启动已使用 SQLAlchemy create_all 初始化缺失表，本轮移除迁移脚本、配置、依赖和发布引用，保持现有数据库与任务数据，不自动升级旧表或重建数据库。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 migrations 目录和 alembic.ini 删除，项目依赖及锁文件不再包含 Alembic，打包不再引用迁移脚本
- [ ] #2 首次初始化数据库可建表，重新打开已有数据库后任务记录保留
- [ ] #3 产品文档与项目约定明确不提供数据库结构自动升级，后续变化另行确认方案
- [ ] #4 当前运行服务和数据保持完整，改动交待验收且不自动提交
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 核对现有建表调用不依赖 Alembic，固定 4 个待删除文件与当前配置、数据基线。2. 删除迁移脚本及配置，使用 uv 离线更新依赖和锁文件，不同步正在运行的环境。3. 移除打包及 AGENTS 引用，通过 CLI 更新 Product 并记录用户决策。4. 仅验证数据库初始化与已有数据保留、配置锁文件一致和服务健康；清理本轮临时文件后交待验收。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25：按用户明确决定删除 migrations 下 3 个脚本和 alembic.ini 共 4 文件；移除 MANIFEST 打包引用和 Alembic 依赖，uv.lock 同时移除仅由其引入的 mako、markupsafe，其余已锁定包版本不变。uv remove 使用 no-sync/offline，运行环境未同步以保持现有服务；uv lock --check --offline 通过。临时独立数据库验证创建 5 张表，保存任务后关闭并重新打开，任务状态和 payload 保留，运行初始化未导入 Alembic。Product 和 AGENTS 说明不支持现有表结构自动升级，用户决定登记为 accepted 的 decision-2。当前 SQLite 未重建、任务和下载数据未删除；Dashboard 及应用健康检查通过。git diff --check 通过；未重复运行全量、前端或视觉测试。验证脚本和临时数据库已清理；未提交 Git，等待用户验收。
<!-- SECTION:NOTES:END -->
