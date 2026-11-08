---
id: TASK-30
title: 实现 DRAFT-6 通用字段模型与请求编译闭环
status: 待验收
assignee: []
created_date: '2026-10-26T13:05:00Z'
updated_date: '2026-10-26T13:52:00Z'
labels: []
dependencies: []
documentation:
  - .backlog/drafts/draft-6 - PRD-数据集字段统一显示规则.md
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户已明确批准实施 DRAFT-6。将字段结构、分组激活和真实请求转换统一，解决全量调查发现的日期范围、单点和互斥组缺口，并接入 Web/CLI/AI 与镜像文件表格。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 完整分类当前可获取的官方表单，保留分组、范围、条款与帮助并准确标识适配状态
- [ ] #2 单选与请求类型分离，日期和单点有官方编码依据，编译器在预览及创建时校验
- [ ] #3 通用控件、互斥分支、长列表、文件表格和 AI 联动功能可验证
- [ ] #4 完成定向测试、完整元数据分类核对及文档更新，保留用户验收权
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
实现领域 schema 与规范化；核对官方转换；实现请求编译与缓存标识；接入 API/CLI/AI；完成前端选择器、互斥组和文件表格；定向测试、全目录核对并更新运行实例。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
新模型全目录只读分类结果（不等于全组合下载验收）：{"datasets": 145, "states": {"full": 144}, "failures": {"provider-c3s-data-rescue-without": "HTTP 404"}, "field_nodes": 1268, "field_types": {"choice": 331, "multiple": 627, "info": 195, "area": 50, "exclusive": 51, "date_range": 7, "location": 7}, "diagnostics": {}}

DRAFT-6 已实施：domain/schema.py 建立分组、根节点、定义指纹、能力和诊断；官方适配完整保留 children 引用、区域边界、默认分支、独立说明与条款。request_compiler.py 统一激活分支、类型/选项/范围验证与请求转换；日期范围输出 [start/end]，单点输出 latitude/longitude 对象，编码依据为官方当前前端 FormRequest 与 DateRange 实现。HTTP 编辑流程携带 schema_revision/editor_values，预览和创建共同编译，拒绝参数不一致和旧定义；CLI 新增 request compile，preview/task create 增加 --schema-check 与 --prefix，原有未绑定元数据的通用 payload 模式继续可用。
前端实现通用单选/多选/日期/单点/区域/对象控件和互斥组、分类去重、861 项列表按需渲染及键盘定位、已选项取消、NCAR 文件表格/分页、条款链接、原子 AI 分支回填/撤销。参考 Arc 的紧凑边框与分段布局，不增加 UI 依赖。元数据刷新显式绕过缓存，保留输入并提示失效，提供重置最新默认值。源码未改数据库、凭据、队列或监听策略。
验证：82 个不同相关后端测试分批通过（编译器 19、字段编辑 16、AI 26、镜像 21），TS/Vite 构建和 git diff --check 通过。全量只读分类 145 条：144 份表单共 1268 节点全部 full、无结构诊断；1 项 form.json 404。full 指当前控件分类及已确认编码，不代表所有组合下载成功。Browser plugin not available，沿用已有授权以 Playwright CLI 完成 12 组主流程和 4 组强制刷新/输入保留/失效移除/最新默认值检查，无页面运行错误；另核对条款协议过滤和撤销后的分支默认值。没有截图或视觉验收。
当前真实 8000 实例带原有进程级代理更新，在实际 ERA5 single levels 和 timeseries 的字段 API 均取得 online/full，并以真实字段定义、真实本地编译器完成小请求预览 HTTP 200；未向 CDS 提交下载、未创建生产任务、未调用真实 AI。具体来源、编码依据与限制记录于 Product。用户验收项保持未勾选，未提交 Git。
<!-- SECTION:NOTES:END -->
