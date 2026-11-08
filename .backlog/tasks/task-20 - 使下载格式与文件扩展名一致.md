---
id: TASK-20
title: 按真实结果元数据交付文件名与类型
status: 待验收
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-27T16:32:00Z'
labels:
  - migration
milestone: m-2
dependencies: []
references:
  - src/ecmwf_downloader/application/request_builder.py
documentation:
  - .backlog/docs/product/doc-1 - Product.md
priority: medium
type: bug
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
默认扩展名只参考数据格式，download_format=zip 可能得到 .nc 文件名，妨碍用户和科研读取工具识别实际文件。

来源为旧 TODO 中未完成事项；迁移仅登记待办，不授权自动扩大本轮开发。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 结果文件名、类型、字节数以源站资产或对应文件响应头为准，不按请求格式强行改扩展名
- [ ] #2 NetCDF、GRIB、ZIP 元数据与多结果、零字节及未知值完成定向检查，真实与模拟证据分开记录
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-28 DRAFT-7 移除本地文件命名/下载。CDS 读取资产名称或 URL 路径与类型，NCAR 返回原文件名及 HEAD 元数据。NC/GRIB/ZIP 使用 SDK 替身验证，零值、未知值与多结果由 API/UI 验证；真实 CDS 与两个 NCAR 仅验证元数据及链接，不读取文件内容。
<!-- SECTION:NOTES:END -->
