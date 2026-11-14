---
id: TASK-43
title: 添加全局网络代理并统一设置保存
status: Done
assignee:
  - '@codex'
created_date: '2026-11-11T05:42:00Z'
updated_date: '2026-11-11T10:37:00Z'
labels: []
dependencies: []
documentation:
  - doc-1
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户要求代理覆盖全部出站操作，包括 CDS、NCAR 镜像和 AI。设置页沿用现有开关，提供系统与手动代理模式，右上角一次保存全部设置，AI 测试按钮位于 API Key 右侧。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 全局代理支持关闭、系统及手动模式，覆盖 CDS、镜像与 AI，旧代理地址可迁移。
- [ ] #2 系统模式读取后端系统代理；WSL 缺少代理环境变量时能使用可达的 Windows 系统代理。
- [ ] #3 页面只在右上角保存一次，代理、AI 凭据与请求监视一并保存，两个测试操作各自独立。
- [ ] #4 设置页直接显示可编辑的 AI API Key，测试使用当前输入，清空后明确处理。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用出站传输配置和现有配置事务，扩展到镜像与 AI。集中管理设置表单草稿，沿用开关并在 API Key 右侧放置测试。定向验证系统、直连、手动、旧配置及真实镜像和字段请求。

设置表单从本机专用接口读取 AI 密钥并直接填入，测试使用当前值。统一保存区分省略与显式清空，验证现有配置和表单操作。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
WSL 直连 CDS HTTPS 超时，经 Windows HTTP 代理访问 CDS 官方目录返回 200。当前本地实例已启用经验证的代理，真实连接测试通过，ERA5 single levels 强制刷新获得 12 个在线字段。89 项定向回归通过，覆盖旧配置、热保存、测试不落盘、环境代理优先级、凭据遮蔽和主要 CDS 调用路径。前端构建及浏览器功能检查通过，浏览器验证了真实探测和模拟启停保存。源站写操作用模拟客户端验证。

用户调整需求后，代理已扩展至 CDS、NCAR AWS/GDEX 和 AI。真实 WSL 系统模式解析到 Windows 代理，取回 CDS 12 个在线字段及两个镜像各 62 个目录条目。102 项定向测试通过，覆盖代理模式、旧配置读取、统一配置事务、凭据隔离、镜像 HEAD 与 AI 测试路由。前端构建及浏览器功能检查通过，实测网络探测，模拟 AI 测试和右上角统一保存。新版实例已启动，旧手动地址自动迁移。

复现旧版 AI 测试请求夹带 has_api_key、sdk_available、ready 等状态字段，导致 HTTP 422。新版测试仅发送有效字段，设置页从本机同源接口直接填入已保存密钥；清空后需关闭 AI 才能保存。56 项相关测试及前端构建通过。新版实例已启动，浏览器点击测试后实际获得 HTTP 200 和模型响应。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
设置页统一保存代理、AI 和请求监视。全局网络代理支持关闭、系统与手动模式。AI API Key 直接显示，连接测试使用当前输入并通过实际服务验证。
<!-- SECTION:FINAL_SUMMARY:END -->
