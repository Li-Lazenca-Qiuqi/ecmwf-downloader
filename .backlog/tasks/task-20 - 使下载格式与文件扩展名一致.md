---
id: TASK-20
title: 使下载格式与文件扩展名一致
status: To Do
assignee: []
created_date: '2026-10-23T15:01:00Z'
updated_date: '2026-10-25T08:19:00Z'
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
- [ ] #1 NetCDF、GRIB 与 ZIP 的命名匹配实际请求格式
- [ ] #2 覆盖格式组合的定向回归并记录规则
<!-- AC:END -->
