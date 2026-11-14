---
id: TASK-38
title: 完善 AI 服务配置与连接测试
status: Done
assignee:
  - '@Codex'
created_date: '2026-11-09T11:13:00Z'
updated_date: '2026-11-11T06:54:00Z'
labels: []
dependencies: []
references:
  - frontend/src/features/settings/AIServiceSettings.tsx
documentation:
  - .backlog/docs/product/doc-1 - Product.md
type: enhancement
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
整理配置表单和开关说明，允许明文编辑 Key，模型设为 luna，可测试当前表单配置。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 模型配置为 luna，API Key 输入可直接阅读，配置接口继续保护已保存的凭据。
- [ ] #2 测试连接使用表单地址、模型、Key 与 JSON 模式，不自动保存，结果在表单中反馈。
- [ ] #3 说明启用补全与 JSON 模式各自控制的行为。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
复用现有兼容服务客户端及安全错误处理，增加草稿连接测试并调整设置卡片和弹窗。用替身验证成功、错误与配置保留。

将两个开关移到设置页，保留默认 JSON。修正官方 GPT-6 Chat Completions 的令牌与采样参数，验证 Luna 的真实连接。

按用户确认统一使用现代 OpenAI Chat Completions 请求参数，测试连接与参数补全都发送 max_completion_tokens，兼容地址按模型应用参数规则。

将 AI 服务配置移到设置首页，标题栏启用开关取代状态标签。开关保存已存配置，表单草稿由保存按钮提交。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
现有 8000 实例模型已改为 luna。65 项相关后端测试和前端构建通过，测试服务采用 HTTP 模拟验证当前表单配置、JSON 模式、失败提示和不写入配置。Playwright 验证 375px 弹窗、明文输入、开关说明及测试反馈。8000 重启后验证无 Key 时返回安全提示。当前未配置 Key，未执行真实模型请求。

已将补全与 JSON 模式开关移到设置页独立保存，JSON 默认开启。真实 OpenAI gpt-6-luna 请求返回 400 unsupported_parameter max_tokens，调整官方 GPT-6 的令牌和采样参数后，在 JSON 模式下应用连接测试返回 200。30 项 AI 定向测试、前端构建和 375px 开关交互验证通过。

按用户确认，测试连接与参数补全统一发送 max_completion_tokens，模型规则不再依赖服务域名。31 项 AI 定向测试通过，覆盖官网地址、模拟兼容地址和带命名空间的 Luna 模型名。本地实例重启后通过官方 gpt-6-luna 的真实 JSON 模式连接测试。

AI 服务表单直接显示在设置首页，标题栏用启用开关表达状态。1200px 与 375px Edge Playwright 模拟接口验证直接编辑、开关独立保存并保留草稿、连接测试失败和重试、显式保存清空 Key 输入。前端构建通过，已核对现有实例的静态资源。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
设置首页直接配置和测试 AI 服务，启用开关位于卡片标题栏。JSON 默认开启，当前 Luna 的真实连接此前已通过。
<!-- SECTION:FINAL_SUMMARY:END -->
