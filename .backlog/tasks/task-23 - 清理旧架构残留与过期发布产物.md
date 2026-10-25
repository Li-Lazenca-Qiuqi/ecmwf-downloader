---
id: TASK-23
title: 清理旧架构残留与过期发布产物
status: Done
assignee: []
created_date: '2026-10-25T12:43:00Z'
updated_date: '2026-10-25T14:00:00Z'
labels:
  - cleanup
dependencies: []
priority: medium
type: chore
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
0.5.0 已使用独立 ecmwf_downloader 包。用户于 2026-10-25 先确认删除 37 个旧架构及发布文件和可再生成缓存，随后明确授权删除 3 个旧配置，并清理确认无文件的 3 个前端脚手架目录。当前源码、新架构测试、app/secrets 配置、任务数据库、下载数据、依赖与运行服务保留，不备份、不自动提交。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 已批准的旧源码、旧测试、空包标记、归档说明、过期 dist、3 个旧配置和 3 个空前端目录全部移除
- [ ] #2 打包、测试覆盖率和项目文档不再将已删除目录作为当前有效入口
- [ ] #3 新架构测试证据保留，服务可访问，当前 app/secrets 配置及任务和下载数据完整；旧配置按用户补充授权删除
- [ ] #4 用户已有任务状态和未提交改动完整保留，本轮仅交付待验收且不自动提交
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 固定删除清单及数量，保存已有未提交修改和配置数据的元数据基线。2. 在确认边界内删除 37 个旧文件与可再生成缓存，清除随之空出的目录，不备份。3. 修正 MANIFEST.in、pyproject.toml、测试导入配置和 AGENTS，通过 CLI 更新 Product。4. 禁用字节码、pytest 缓存及覆盖率生成，仅运行新架构测试，并验证服务和文档引用；清理本轮临时脚本后交待验收。

用户补充授权：删除 config/accounts.yaml、config/ai_config.yaml、config/default_config.yaml，以及确认无文件的 frontend/src/pages、styles、components 空目录。先核对清单，当前 app/secrets 配置和数据库不变；migrations 为有效 Alembic 代码予以保留。同步 Product 和 AGENTS，仅做配置边界及服务检查，不重复已通过的新架构测试。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-25：按用户确认删除 37 个指定旧文件及 23 个 Python 缓存文件，旧源码、旧测试、空包标记、无用途归档说明和过期 dist 均已移除，未备份。MANIFEST 移除旧目录排除项，覆盖率目标改为 ecmwf_downloader，测试导入配置仅指向当前源码；AGENTS 与 Product 同步。保留的新架构测试 14 passed，1 条既有 Starlette/httpx 弃用警告；执行时禁用字节码、pytest 缓存和覆盖率生成。AST 检查无旧架构导入，3 个文档链接有效，git diff --check 通过。原当前包、新测试与既有其他任务文件内容摘要一致；配置和下载数据保留，两个服务健康检查通过，调度器保持运行。用户对 TASK-1、TASK-22 的 Done 状态和未提交修改保留。历史 299 项测试不再代表当前测试数量，本轮不重建发布包、不做视觉验证、不提交 Git。等待用户验收，验收项未勾选。

2026-10-25 补充清理：已删除 config/accounts.yaml、config/ai_config.yaml、config/default_config.yaml，共 5169 字节；未读取或输出其凭据内容，未备份。已删除 frontend/src/pages、styles、components 三个空目录。Product 与 AGENTS 已同步，当前 app/secrets 及示例内容摘要一致、运行锁保留、数据库文件完整、其他任务记录未改动；两个服务检查通过。migrations 为仍在使用的 Alembic 数据库版本代码，保留。git diff --check 通过，本次未重复运行代码测试或视觉验证。临时清理脚本已删除，交待验收，不代设完成。
<!-- SECTION:NOTES:END -->
