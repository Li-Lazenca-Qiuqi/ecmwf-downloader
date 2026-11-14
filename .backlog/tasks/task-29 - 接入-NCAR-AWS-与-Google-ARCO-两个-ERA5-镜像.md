---
id: TASK-29
title: 接入 NCAR AWS/GDEX 原文件链接并移除 ARCO 本地导出
status: Done
assignee: []
created_date: '2026-10-26T10:11:00Z'
updated_date: '2026-11-08T12:49:00Z'
labels: []
dependencies: []
type: feature
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 DRAFT-5 和 DRAFT-7 的当前范围提供 NCAR AWS 与 NCAR GDEX。各自展示真实文件目录并返回所选原文件链接，与默认 CDS 并列作为可选来源。请求字段帮助可按需展开。ARCO 本地导出已按 DRAFT-7 取消。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 NCAR AWS/GDEX 独立列真实目录和文件，返回原文件链接，不依赖 CDS 账号；ARCO 本地导出及相关依赖移除
- [ ] #2 CLI/API/Web 创建链接请求并由队列解析，取消/失败真实显示，不进行本地文件发布或修改 CDS 账号计数
- [ ] #3 两个 NCAR 源链接生成及仅 HEAD 的定向回归通过，真实目录与文件响应头验证单独记录且无文件体传输
- [ ] #4 CDS 作为正常来源并列显示，不标注保留；请求字段不铺开完整数据集介绍，字段帮助默认折叠且可展开
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
核对实时元数据与网络路径；以独立 dataset_id 路由两源、不更改表结构；实现 NCAR 文件目录与直下、ARCO 元数据和子集导出；接入调度器无账号消费、CLI 与添加任务页；定向回归并记录真实读取/下载证据。

用户已开启 Windows 代理局域网监听，WSL 经当前主机地址访问两源均为 HTTP 200。仅为当前后端进程设置代理并重启空闲实例；使用独立临时工作区进行两源真实 HTTP 创建、队列消费、内容与来源验证，不在生产库创建验收任务。

加入独立 NCAR GDEX HTTPS 文件来源并验证其自身文件目录与真实下载；前端补齐来源选项，去除 CDS 保留标签，移除数据集长介绍，将字段帮助折叠；做相关 API/队列/页面定向验证。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
两镜像端到端实现已完成：NCAR 在线目录/原文件，ARCO 动态元数据/时空压力层子集导出；独立 dataset_id 记录来源，无表结构变更，无账号队列消费，不更改 CDS 计数，保留 .part/取消/重试。15 项镜像测试与 42 项相关回归通过（57 个不同测试），TS/Vite 构建及 10 项模拟 UI 功能检查通过。通过 Windows 代理取得真实 NCAR 陆海掩膜与 Google 2m 温度小请求，在 WSL 校验解码与 NetCDF 导出；具体哈希、时间、网格、单位、数值及流量见 Product 文档。WSL 直连仍失败，需可达代理，不能宣称本机后端连续真实下载已验收。未改真实用户配置/账号/数据，未在生产库建下载任务。临时文件待最后清理，用户验收条件保持未勾选。

收尾检查：本轮 Windows 安装包临时目录与 3 个验证脚本的清理被自动审批阻止，原因为 blocked by policy，未提供更多说明；安全缩小为逐文件清理后仍被拒绝。临时包保留在 Windows TEMP 的 ecmwf-mirror-wheels-o4gavtf6，脚本为 ecmwf_mirror_wheels.py、ecmwf_mirror_real_check.py、ecmwf_mirror_ui_qa.py，均无用户数据。WSL 临时数据样本和 TS 构建中间产物已清理。

网络阻塞已解除：用户开启代理局域网监听，WSL 经 Windows 代理获取两源元数据均成功。独立临时工作区/全新库/零账号，真实 FastAPI HTTP 预览创建两任务，真实 Scheduler/Provider 通过 requests/fsspec 消费，均 queued→running→completed、account_id=null、最终文件发布且 .part 不残留。NCAR LSM 766274 字节，网格 1×721×1440、有限且 0–1；ARCO 2m_temperature 指定时空子集导出 10082 字节、1×5×5、单位 K、274.697998046875–278.38763427734375，时间与来源元数据正确。哈希和请求范围见 Product。当前 8000 服务带进程级代理重启，字段 API 在线返回 NCAR 62 文件与 ARCO 273 变量/8 字段，scheduler_running=true，生产任务仍为零。未改全局配置、真实账号或生产数据；临时样本已清理。继续待验收，不勾选条件、不提交。

加入独立 NCAR GDEX 来源，使用自身 THREDDS 目录与 HTTPS 原文件，输出采用 gdex_ 前缀；21 项镜像定向测试、前端构建、6 项页面功能检查通过（真实 GDEX 目录/选择/预览，CDS 长介绍使用模拟字段核对）。独立临时库零账号真实队列下载 GDEX LSM：766274 字节，SHA256 与已验证 AWS 样本一致，NetCDF 1×721×1440、全部有限且 0–1，无 .part 残留，样本和临时工作区已清理。证据见 Product，不代替用户验收。未提交 Git。

2026-10-28 用户确认 DRAFT-7 后取消 ARCO 本地导出条款。真实 AWS 与 GDEX 各列出 62 个 202401 地表文件；2m_temperature 对应链接请求 f756ecac-afad-4358-a0c3-7931c843a4b9 / 985b2d64-52ca-4d36-bcb1-5c2133359165 均 completed、1 条链接、HEAD 元数据 1134576716 bytes、account_id 为空。没有传输大文件；目录分页、URL/HEAD、ARCO 拒绝和多文件请求有模拟检查。
<!-- SECTION:NOTES:END -->
