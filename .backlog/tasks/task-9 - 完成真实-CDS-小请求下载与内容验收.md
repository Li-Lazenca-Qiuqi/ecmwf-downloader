---
id: TASK-9
title: 完成真实 CDS 小请求提交监视与链接验收
status: 待验收
assignee: []
created_date: '2026-10-23T15:00:00Z'
updated_date: '2026-10-27T16:32:00Z'
labels:
  - migration
  - live-cds
milestone: m-0
dependencies: []
references:
  - doc/note/cds_smoke_request.yaml
  - .backlog/drafts/draft-1 - PRD-0.5.0_acceptance.md
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: high
type: task
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DRAFT-7 已获用户确认：验收目标改为提交、监视与链接交付，不下载数据文件。请求附件仍为 2m_temperature、2024-01-01 00:00 UTC、area=[31,120,30,121]、NetCDF；旧下载内容/目录要求已取消，不能据此标记旧下载功能验收完成。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 项目 Worker 真实提交用户指定 ERA5 小请求，记录变量、UTC 时间、区域和 NetCDF 参数及实际日期
- [ ] #2 远端 successful、本地 completed，返回真实 HTTPS 结果链接及官方可用大小和类型，不下载文件
- [ ] #3 服务重启后用同一远端 ID 更新结果，不重复提交，CLI/API/页面提供一致链接且不泄露凭据
- [ ] #4 明确缓存有效期未知和未验证范围；本地不生成科学数据文件，不再要求下载目录或内容验收
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-28 Asia/Shanghai：真实本地请求 5ee5b866-4fb9-493d-9fa6-939ff8c191d9，远端 705a3724-4ffd-49f6-b126-c12a5ca62c7d，successful/completed，1 条链接、官方 25171 bytes。停服务后 CLI refresh，再启动服务，仍查询同一 ID 并恢复链接；另用 SDK 比对源站数据集及请求参数一致，CLI links JSON 与 API URL 一致且无 API Key。没有读取科学文件体、未创建下载文件；没有做旧内容验收或真实远端取消。验收项未勾选。
<!-- SECTION:NOTES:END -->
