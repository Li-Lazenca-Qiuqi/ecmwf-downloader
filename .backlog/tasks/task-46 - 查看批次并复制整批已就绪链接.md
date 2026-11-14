---
id: TASK-46
title: 查看批次并复制整批已就绪链接
status: Done
assignee:
  - '@codex'
created_date: '2026-11-11T11:53:00Z'
updated_date: '2026-11-14T02:54:00Z'
labels: []
dependencies: []
documentation:
  - doc-1
priority: medium
type: enhancement
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
源自 DRAFT-8，沿用 TASK-42 的批次 ID 和固定份次。跨页拆分请求需要一个按批次交付链接的入口。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 从批次内任一请求打开批次，按原序号显示份次、状态、已就绪份数及原总份数。
- [ ] #2 一次复制该批次全部已就绪链接，并显示实际复制的链接数。超出已加载范围、被当前筛选隐藏的份次也纳入。同名不同批次分别处理。
- [ ] #3 未就绪或已删除的份次不妨碍复制其余链接。旧记录没有批次 ID 时仍可复制单条。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
使用既有批次 ID 和份次查询整批，复用队列详情弹窗和链接复制；验证筛选、分页与同名批次。

在多份请求行显示整批复制入口，以批次 ID 获取全部就绪链接，剪贴板不可用时打开整批详情供手动复制。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
API 回归验证同名批次隔离、删除份次、链接按原份次顺序返回。Playwright 从首屏的请求复制含第 23 份的整批链接，并检查剪贴板拒绝时提供文本框。

多份请求行直接复制整批。Playwright 用实际 NCAR 40 条批次验证首屏保持 20 条时整批复制 40 条，模拟剪贴板拒绝后打开详情并提供全部链接。生产构建通过。

整批入口合并到行内复制图标，Ctrl 切换带加号的浅蓝样式。生产构建通过，Playwright 使用真实 40 条批次与模拟剪贴板验证普通点按复制 1 条、Ctrl 点击复制 40 条、松开恢复及剪贴板失败回退。

队列行内、工具栏与详情中的普通复制和整批复制共用右下角成功提示。构建通过。Playwright 使用实际镜像批次和模拟剪贴板验证 1 条及 40 条复制、详情内提示、右下角定位、自动收起和失败提示。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
从请求详情进入批次，按固定份次展示并一次复制已就绪链接。
<!-- SECTION:FINAL_SUMMARY:END -->
