---
id: TASK-50
title: PRD AI 参数补全的推理强度选项
status: 待验收
assignee:
  - '@Codex'
created_date: '2026-11-16T07:14:00Z'
updated_date: '2026-11-17T01:36:00Z'
labels: []
dependencies: []
references:
  - DRAFT-8
documentation:
  - doc-1
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 需求

在设置页的 AI 服务区增加「推理强度」，按当前模型提供全部已知支持档位。

## 交互与默认值

- 下拉显示「服务默认」和当前模型支持的全部档位。切换模型时更新列表。GPT-6 Luna 提供关闭（none）、低（low）、中（medium）、高（high）、超高（xhigh）、最高（max）。
- 未知的兼容模型只显示「服务默认」。模型能力根据官方发布的模型 ID 及可识别别名匹配。换模型时，若原档位不再可用，切换到该模型的「服务默认」。
- 旧配置未填写推理强度时，Luna 沿用 none，其他模型沿用原行为。显式选择「服务默认」时省略 reasoning_effort，由服务决定。
- 设置页统一保存。JSON 模式和 4096 tokens 的生成上限沿用当前默认。推理和最终 JSON 共用上限，达到上限时显示截断提示。

## 参考

- [Chat Completions 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [模型推理能力](https://developers.openai.com/api/docs/guides/reasoning?api-mode=chat)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 切换模型即更新下拉。Luna 显示服务默认与全部六档，未知模型显示服务默认。
- [ ] #2 保存后重新打开仍显示所选值。连接测试使用表单当前选择，参数补全使用已保存选择。显式选择服务默认时省略 reasoning_effort。
- [ ] #3 旧 Luna 配置仍使用 none，旧配置下的其他模型保持原请求行为。请求截断、服务拒绝推理档位和超时有各自的错误提示。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 核对官方模型能力，将已知档位集中在后端，由设置接口提供给前端筛选。
2. 将推理档位接入统一保存、表单连接测试和参数补全，兼容旧配置并区分截断、超时和参数拒绝。
3. 用模拟 AI 服务验证请求参数和回退规则，构建前端并记录验收办法。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
42 项相关后端测试通过，覆盖各 Luna 档位、服务默认省略字段、旧配置、截断、超时和服务拒绝。使用模拟 OpenAI 兼容端点。TypeScript 和 Vite 构建通过。内置浏览器连接未配置，改用隔离的 Playwright/Edge 实测设置页。旧 Luna 显示关闭，菜单含六档和服务默认，最高保存并刷新后恢复。切到未知模型立即显示服务默认，保存后 API 返回 default。控制台无错误。

验收调整。AI 服务首行并排显示服务地址、模型名称和 Reasoning Effort，API Key 与连接测试在下一行。Reasoning Effort 的标题和档位均改为英文。生产构建通过，运行实例已返回本次资源。

保存配置成功后复用右下角提示卡片，约 3.5 秒自动消失。已验证模拟保存成功与失败。奶茶鼠于 2026-11-17 确认 TASK-50 验收通过。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
已实现设置页按模型展示推理档位。连接测试使用表单选项，补全读取保存值，服务默认由服务端决定。验收时在设置页切换 Luna 和未知模型，并保存后刷新核对。
<!-- SECTION:FINAL_SUMMARY:END -->
