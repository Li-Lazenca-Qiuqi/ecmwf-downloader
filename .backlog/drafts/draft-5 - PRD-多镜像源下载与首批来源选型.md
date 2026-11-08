---
id: DRAFT-5
title: PRD 多镜像源下载与首批来源选型
status: Draft
assignee: []
created_date: '2026-10-26T09:54:00Z'
updated_date: '2026-10-27T16:21:00Z'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 已确认范围

用户确认接入 NCAR AWS ERA5、NCAR 自有 GDEX ERA5 和 Google ARCO ERA5，实施由 TASK-29 跟踪。CDS 作为正常数据来源与三个镜像并列显示，界面不标注“保留”。实时预报 AWS/Google/Azure 不属于本轮；代理不代替用户验收。

## 来源与下载行为

NCAR AWS：公开 s3://nsf-ncar-era5，产品 ID mirror-ncar-era5。按产品/年月目录完整分页列出 NetCDF 文件和大小，每文件一个任务。

NCAR GDEX：产品 ID mirror-ncar-gdex-era5，由 tds.gdex.ucar.edu 的 d633000 THREDDS 目录获取文件列表，通过 data.gdex.ucar.edu/d633000 HTTPS 下载原文件。与 AWS 独立列目录和下载，不以 AWS 列表代替自身目录。两种 NCAR 来源都不提供区域裁剪、转换或日期拆分；默认文件名分别采用 ncar_、gdex_ 前缀，避免同名碰撞。

Google ARCO：公开 gs://gcp-public-data-arco-era5，产品 ID mirror-arco-era5；读取 ar/full_37-1h-0p25deg-chunk-1.zarr-v3（实际为 Zarr 2）。变量、压力层和 ERA5/ERA5T 截止日期从真实元数据读取，支持时空子集并导出 NetCDF4，不插值。小区域也可能读取完整云端数据块。

## 队列与界面

来源编码在独立 dataset_id 内，不改数据库结构。镜像无需 CDS 账号，沿用自动开始的单队列、取消/重试、事件与 .part 原子发布，不能修改 CDS 账号计数。Web 默认 NCAR AWS，可选择 GDEX、ARCO 或 CDS。请求字段不铺开完整数据集介绍；字段帮助默认折叠，需要时展开。AI 位于右侧预览上方，服务配置在设置页。CLI/API 复用相同请求构建与 Worker。

## 验收要求

真实列目录，不伪造字段或变量，失败明确显示。三个镜像的创建、下载或导出、取消、输出命名和来源追踪做定向验证；真实联网证据与模拟测试分开记录，验收由用户完成。当前 WSL 已经由用户开放的 Windows 代理访问镜像；进程采用 HTTP_PROXY/HTTPS_PROXY 与本机 NO_PROXY，不改全局网络配置，不据此宣称无代理直连成功。

## 接入依据

https://registry.opendata.aws/nsf-ncar-era5/
https://gdex.ucar.edu/datasets/d633000/dataaccess/
https://ncar.github.io/gdex-intake-esm/era5/
https://github.com/google-research/arco-era5
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
本轮 WSL 环境对 NCAR ERA5 AWS、Google ARCO ERA5、AWS forecast、Google forecast 四个公开云桶进行了 max-keys=1 的只读目录探测，均出现网络请求失败；没有读取气象文件，也未据此判断站点停止服务。公开维护方文档已核对，用户实际运行环境的可达性和吞吐仍待实测。

用户已明确确认首批接入 NCAR AWS ERA5 与 Google ARCO ERA5，不接入实时预报镜像。实施继续复用现有单队列，来源编码在明确的 dataset_id 中，不修改数据库表结构。NCAR 下载已发布文件，ARCO 做变量/时空子集导出；现有 CDS 保留但界面优先显示镜像。

用户开启 Windows 代理的局域网监听后，WSL 两源访问与真实 HTTP 创建/队列消费均已通过；不再受原网络阻塞。只为当前后端进程提供 HTTP_PROXY/HTTPS_PROXY 与本机 NO_PROXY，未写全局网络配置；后台重启需保留可达代理环境变量。真实小样本证据见 Product 文档，用户验收仍待进行。

用户进一步要求加入 NCAR 自有 GDEX 站点作为独立数据来源，CDS 与其他来源平等展示，不标注保留；请求字段页不铺开长篇数据集介绍，详细字段帮助默认收起。先核对 GDEX 当前匿名文件下载与目录接口，不将需登录的定制子集功能混入原文件下载。

2026-10-28 经用户确认的 DRAFT-7 已实施：软件改为提交请求、监视远端状态并交付链接；取消本地下载、输出目录/浏览/覆盖、传输进度和 ARCO 本地导出。请求字段、AI、官方规模与年月日拆分等仍适用；本草案中冲突的旧输出/下载要求被新路线取代，不代表旧要求已修复或重新验收。实施证据见 TASK-32。
<!-- SECTION:NOTES:END -->
