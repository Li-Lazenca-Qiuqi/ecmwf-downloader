---
id: DRAFT-1
title: 'PRD: 0.5.0_acceptance'
status: Draft
assignee: []
created_date: '2026-10-25T08:18:00Z'
updated_date: '2026-10-27T16:21:00Z'
labels:
  - requirements
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
<!-- source: doc/PRD/0.5.0_acceptance.md -->

# 0.5.0 收尾验收

日期：2026-10-07。状态：本轮范围已确认，真实下载存在外部阻塞。来源：用户同意补齐文档、待办并执行真实下载与管理台验收；后续指定使用小请求并允许临时 Playwright 自动化。

2026-10-23 流程更新：本文件保留 0.5.0 当时确认的范围；进度与阶段规划迁入 Backlog，旧测试结果仅作为历史证据。所有任务转交用户验收，代理不代勾验收项或设为 Done。新规则要求按明确功能做定向测试，不主动重复视觉或全量验证；本次迁移未重跑本表测试。

## 目标与范围

将已有 CLI + Web 重构整理成可追踪的产品现状与验收证据，确认源码、前端和 wheel 的基本运行路径，并修复本轮直接阻断验收的新增账号 API。保持 0.5.0 版本和现有架构。

验收使用独立配置、SQLite 和输出目录；原有数据与真实账号配置完整保留。浏览器使用虚构账号和 `--no-worker`，避免产生无效外部请求。真实 CDS 验收需本地凭据与数据集访问条件；密钥不可进入源码、文档、截图或日志。

## 通过标准

| 项目 | 标准 | 证据入口 |
| --- | --- | --- |
| 文档 | 规定的文档文件与分类目录存在，AGENTS 可导航，Backlog 区分待办、待验收和外部阻塞 | `doc/`、`.backlog/`、`AGENTS.md` |
| 账号 API | 省略 ID 成功生成 ID；显式 ID 保留；响应不含 key | `tests/test_new/test_api.py` |
| Python | 本轮相关回归和既有测试通过，警告单独记录 | 验收记录 |
| 前端 | TypeScript 与 Vite 生产构建成功 | 验收记录 |
| 分发 | wheel 在独立环境安装；运行时无 Node；CLI、Web、SPA 与资源正常 | 验收记录 |
| HTTP/SSE | 预览、创建、入队、取消和事件重连真实 HTTP 验证通过 | 验收记录 |
| 浏览器 | 页面身份、非空、无框架错误、控制台、截图及操作后状态检查；记录窄屏结果 | 验收记录 |
| 真实下载 | 选定 CDS 请求完成，任务为 completed，`.part` 消失，文件可读；核对 variable、时间、经纬度、单位和缺失值 | 验收记录 |

已发现的旧功能缺口进入 Backlog，本轮不扩展到全部界面重构或调度器重写。真实下载未成功时，不使用 mock、文件存在或本地预览替代科学内容验收。版本、Git 提交、Tag 和外部发布均不在本轮授权内。
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-28 经用户确认的 DRAFT-7 已实施：软件改为提交请求、监视远端状态并交付链接；取消本地下载、输出目录/浏览/覆盖、传输进度和 ARCO 本地导出。请求字段、AI、官方规模与年月日拆分等仍适用；本草案中冲突的旧输出/下载要求被新路线取代，不代表旧要求已修复或重新验收。实施证据见 TASK-32。
<!-- SECTION:NOTES:END -->
