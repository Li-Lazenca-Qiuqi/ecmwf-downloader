---
id: doc-3
title: 数据集表单字段调查与展示规则依据
type: other
created_date: '2026-10-26T12:20:00Z'
updated_date: '2026-10-27T16:32:00Z'
---
# 数据集表单字段调查

核对日期：2026-10-26。当前官方 CDS 目录 145 项，表单成功 148 项，失败 1 项；表单请求共 145 次，解压后响应体合计 1832521 字节。查询为匿名公开元数据，不使用账号密钥，不创建下载任务，不等同于各数据集下载验收。目录流量与 HTTP/TLS 开销不包含在表单响应体字节数内。

目录接口：https://cds.climate.copernicus.eu/api/catalogue/v1/datasets
表单接口：https://cds.climate.copernicus.eu/api/catalogue/v1/collections/<dataset_id>/form.json

## 控件覆盖

| 官方控件 | 控件数 | 涉及数据集 |
|---|---:|---:|
| DateRangeWidget | 7 | 7 |
| ExclusiveGroupAccordionWidget | 12 | 12 |
| ExclusiveGroupWidget | 39 | 39 |
| FreeEditionWidget | 51 | 49 |
| GeographicExtentWidget | 50 | 50 |
| GeographicLocationWidget | 7 | 7 |
| LicenceWidget | 144 | 144 |
| StringChoiceWidget | 331 | 125 |
| StringListArrayWidget | 76 | 59 |
| StringListWidget | 551 | 137 |

## 当前映射遗漏

- ExclusiveGroupAccordionWidget：12 个数据集，字段 {'geo_group': 12}；示例 derived-era5-pressure-levels-daily-statistics, derived-era5-single-levels-daily-statistics, derived-utci-historical-timeseries, multi-origin-c3s-atlas, projections-cmip6, projections-cmip6-decadal-prototype, projections-cordex-domains-single-levels, reanalysis-cerra-land-timeseries。
- DateRangeWidget：7 个数据集，字段 {'date': 7}；示例 derived-utci-historical-timeseries, reanalysis-cerra-land-timeseries, reanalysis-era5-land-timeseries, reanalysis-era5-pressure-levels-timeseries, reanalysis-era5-single-levels-timeseries, reanalysis-oras5-timeseries, sis-agrometeorological-indicators-timeseries。
- GeographicLocationWidget：7 个数据集，字段 {'location': 7}；示例 derived-utci-historical-timeseries, reanalysis-cerra-land-timeseries, reanalysis-era5-land-timeseries, reanalysis-era5-pressure-levels-timeseries, reanalysis-era5-single-levels-timeseries, reanalysis-oras5-timeseries, sis-agrometeorological-indicators-timeseries。

## 结构与规模

```json
{
  "statistics": {
    "raw_required": 965,
    "normalized_fields": 1268,
    "request_fields": 1034,
    "grouped_fields": 76,
    "defaults_present": 206,
    "children_string_refs": 102,
    "children_dict_refs": 0,
    "area_fields": 50,
    "single_option_choice": 39,
    "date_named_fields": 8,
    "non_global_area_default": 10,
    "single_option_multiple": 16
  },
  "largest_choices": [
    [
      302,
      "insitu-observations-surface-land",
      "year"
    ],
    [
      175,
      "insitu-observations-surface-marine",
      "year"
    ],
    [
      87,
      "derived-era5-single-levels-daily-statistics",
      "year"
    ],
    [
      87,
      "derived-era5-pressure-levels-daily-statistics",
      "year"
    ],
    [
      77,
      "reanalysis-era5-land",
      "year"
    ],
    [
      77,
      "derived-era5-land-daily-statistics",
      "year"
    ],
    [
      62,
      "projections-cmip6-decadal-prototype",
      "base_year"
    ],
    [
      58,
      "projections-cmip6",
      "model"
    ]
  ],
  "largest_multiple": [
    [
      861,
      "seasonal-original-single-levels",
      "leadtime_hour"
    ],
    [
      720,
      "projections-cmip5-daily-single-levels",
      "period"
    ],
    [
      526,
      "projections-cmip5-daily-pressure-levels",
      "period"
    ],
    [
      498,
      "projections-cmip5-monthly-single-levels",
      "period"
    ],
    [
      451,
      "projections-cmip6",
      "year"
    ],
    [
      430,
      "seasonal-original-pressure-levels",
      "leadtime_hour"
    ],
    [
      311,
      "satellite-lake-water-level",
      "lake"
    ],
    [
      296,
      "projections-cmip5-monthly-pressure-levels",
      "period"
    ]
  ],
  "common_field_names": [
    [
      144,
      "licences"
    ],
    [
      142,
      "variable"
    ],
    [
      100,
      "year"
    ],
    [
      96,
      "month"
    ],
    [
      64,
      "day"
    ],
    [
      61,
      "version"
    ],
    [
      50,
      "area"
    ],
    [
      44,
      "global"
    ],
    [
      44,
      "geo_group"
    ],
    [
      44,
      "data_format"
    ],
    [
      38,
      "product_type"
    ],
    [
      27,
      "experiment"
    ],
    [
      21,
      "time_aggregation"
    ],
    [
      21,
      "time"
    ],
    [
      19,
      "period"
    ],
    [
      18,
      "origin"
    ],
    [
      17,
      "temporal_aggregation"
    ],
    [
      13,
      "leadtime_hour"
    ],
    [
      12,
      "model"
    ],
    [
      12,
      "ensemble_member"
    ],
    [
      10,
      "statistic"
    ],
    [
      10,
      "domain"
    ],
    [
      9,
      "region"
    ],
    [
      9,
      "pressure_level"
    ],
    [
      8,
      "temporal_resolution"
    ],
    [
      8,
      "climate_data_record_type"
    ],
    [
      7,
      "system"
    ],
    [
      7,
      "originating_centre"
    ],
    [
      7,
      "location"
    ],
    [
      7,
      "hydrological_model"
    ],
    [
      7,
      "date"
    ],
    [
      6,
      "sensor_on_satellite"
    ],
    [
      6,
      "level_type"
    ],
    [
      6,
      "download_format"
    ],
    [
      6,
      "area_group"
    ]
  ]
}
```

## 原始控件代表结构

以下为语义分析所需的精简代表结构，长选项只保留长度与样例，不作为内置字段定义。

### StringChoiceWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/satellite-aerosol-properties/form.json)，字段 time_aggregation。
```json
{
  "name": "time_aggregation",
  "label": "Time aggregation",
  "required": true,
  "css": "todo",
  "type": "StringChoiceWidget",
  "details": {
    "values": {
      "length": 3,
      "sample": [
        "daily_average",
        "monthly_average"
      ]
    },
    "columns": 3
  },
  "id": "time_aggregation"
}
```

### StringListArrayWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/satellite-aerosol-properties/form.json)，字段 sensor_on_satellite。
```json
{
  "name": "sensor_on_satellite",
  "label": "Sensor on satellite",
  "required": true,
  "css": "todo",
  "type": "StringListArrayWidget",
  "details": {
    "groups": {
      "length": 5,
      "sample": [
        {
          "keys": [
            "label",
            "columns",
            "open",
            "values",
            "labels"
          ]
        },
        {
          "keys": [
            "label",
            "columns",
            "open",
            "values",
            "labels"
          ]
        }
      ]
    },
    "displayaslist": false,
    "accordionGroups": true,
    "accordionOptions": {
      "searchable": false,
      "openGroups": {
        "length": 5,
        "sample": [
          "Dual view VIS-TIR radiometers",
          "Multi-angle VIS polarimeter"
        ]
      }
    }
  },
  "id": "sensor_on_satellite"
}
```

### StringListWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/satellite-aerosol-properties/form.json)，字段 algorithm。
```json
{
  "name": "algorithm",
  "label": "Algorithm",
  "required": true,
  "css": "todo",
  "type": "StringListWidget",
  "details": {
    "values": {
      "length": 14,
      "sample": [
        "aergom",
        "adv"
      ]
    },
    "columns": 1
  },
  "id": "algorithm"
}
```

### LicenceWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/satellite-aerosol-properties/form.json)，字段 licences。
```json
{
  "type": "LicenceWidget",
  "name": "licences",
  "label": "Terms of use",
  "details": {
    "licences": {
      "length": 1,
      "sample": [
        {
          "keys": [
            "id",
            "revision",
            "label",
            "contents_url",
            "attachment_url",
            "spdx_identifier"
          ]
        }
      ]
    }
  }
}
```

### FreeEditionWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators/form.json)，字段 global。
```json
{
  "details": {},
  "name": "global",
  "type": "FreeEditionWidget",
  "label": "Whole available region"
}
```

### GeographicExtentWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators/form.json)，字段 area。
```json
{
  "details": {
    "stepX": 0.01,
    "stepY": 0.01,
    "enableMap": true,
    "range": {
      "n": 90,
      "s": -90,
      "e": 360,
      "w": -360
    },
    "default": {
      "n": 90,
      "s": -90,
      "e": 180,
      "w": -180
    }
  },
  "title": "Area selection",
  "name": "area",
  "type": "GeographicExtentWidget",
  "label": "Area selection"
}
```

### ExclusiveGroupWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators/form.json)，字段 geo_group。
```json
{
  "type": "ExclusiveGroupWidget",
  "name": "geo_group",
  "label": "Geographical area",
  "details": {
    "default": "global"
  },
  "children": {
    "length": 2,
    "sample": [
      "global",
      "area"
    ]
  }
}
```

### ExclusiveGroupAccordionWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators-timeseries/form.json)，字段 geo_group。
```json
{
  "type": "ExclusiveGroupAccordionWidget",
  "default": "location",
  "order": {
    "length": 2,
    "sample": [
      "location",
      "area"
    ]
  },
  "name": "geo_group",
  "label": "Geographical area",
  "details": {
    "default": "location",
    "titles": {
      "location": "Location selection",
      "area": "Area selection"
    }
  },
  "children": {
    "length": 2,
    "sample": [
      "location",
      "area"
    ]
  },
  "id": "geo_group"
}
```

### DateRangeWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators-timeseries/form.json)，字段 date。
```json
{
  "name": "date",
  "label": "Date",
  "required": true,
  "css": "todo",
  "type": "DateRangeWidget",
  "details": {
    "minStart": "1979-01-01",
    "maxEnd": "2026-10-18",
    "defaultStart": "1979-01-01",
    "defaultEnd": "2026-10-18"
  },
  "id": "date"
}
```

### GeographicLocationWidget
来源：[官方表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/sis-agrometeorological-indicators-timeseries/form.json)，字段 location。
```json
{
  "details": {
    "enableMap": true
  },
  "name": "location",
  "type": "GeographicLocationWidget",
  "label": "Location selection",
  "id": "location"
}
```

## 无法取得或解析的表单

{
  "fetch_failures": {
    "provider-c3s-data-rescue-without": "HTTP 404"
  },
  "normalization_failures": {}
}

只保存统计与必要代表结构，全部原始响应仅在调查进程内存中使用，未写入项目快照。当前界面实现未因本次调查改变，新的显示规则另交用户审查。



## 补充核对与解释

三个镜像的真实本机 schema 均返回 online：NCAR AWS 和 GDEX 的默认 202401 地表目录分别为 62 个文件候选、一个 object_key 多选字段；Google ARCO 为 8 个字段，273 个变量、37 个压力层、87 个年份，以及产品版本、月、日、整点与区域。镜像原文件目录不能套用 CDS 裁剪字段。

1268 为原始表单控件总数，包含说明和分组，不等于真正请求字段数。当前统一模型把说明、布局和互斥组独立处理，只有激活分支中的请求字段进入 payload；144 份可取得的表单已完成节点分类，另 1 项 404。结构适配不等于所有远端约束组合或真实下载通过。

102 个 children 引用均为字符串名称，嵌套对象为零。分组必须按名称解析引用，不能靠父子嵌套或相邻顺序判断。51 个互斥组包含 39 个 ExclusiveGroupWidget 和 12 个 ExclusiveGroupAccordionWidget；前一种有一个 date_range，不全是地理分组。

[ERA5 时间序列表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-era5-single-levels-timeseries/form.json)的地理分组默认 location，只允许 location/area 两个分支，没有 global。默认区域为 [52,0,51,1]，最小范围 0.25°、最大范围 2°。因此全部范围不是每个数据集都应出现的默认选项；官方 default 也不等于数据覆盖边界。

[地面站观测表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/insitu-observations-surface-land/form.json)的 geo_group 默认 area。不能对所有数据集强制改成 global。

[CARRA 月平均表单](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-carra-means/form.json)的 levels_help 说明相同层次值在压力层、高度层、模式层下对应不同单位。全部 FreeEditionWidget 一律隐藏会丢掉这些必要帮助；应区分互斥组的无参数分支和独立说明。

provider-c3s-data-rescue-without 的集合元数据返回 HTTP 200，form.json 返回 HTTP 404，disabled_reason=null。已确认不能取得表单，未确认具体原因，不能推断为网络故障、停止服务或不可下载。

另外只读核对 [ERA5 时间序列 Process 描述](https://cds.climate.copernicus.eu/api/retrieve/v1/processes/reanalysis-era5-single-levels-timeseries)：inputs 只列 variable、data_format、area，而表单还含 date 和 location。表单与 Process 描述存在差异；日期与单点的最终请求编码须核对官方生成的 API 示例或转换逻辑，不能猜测，也不能因为 Process 列表缺项就丢弃这两个控件。本轮未创建检索任务验证此转换。

全量 145 次表单响应合计 1832521 字节（约 1.83 MB，含 404 响应），加上目录、三份初始采样、补充元数据和协议开销才是总流量；没有测量代理实际计费流量。原始响应只驻留进程内存，调查脚本已清理。展示规则提案另见对应 Draft，未在本轮修改应用代码或执行全量测试。



## 实施后全目录核对

DRAFT-6 实施后的当前转换器逐项核对同一 145 项目录：144 份有效表单、1268 节点均成功分类，无结构诊断；另 1 项仍为 HTTP 404。归一类型为 choice 331、multiple 627、info 195、area 50、exclusive 51、date_range 7、location 7。先前记录的 3 类遗漏已补齐；本结果是结构与编码覆盖，不是所有约束组合或下载验收。实施和定向验证详见 TASK-30 与 Product，未保留全量原始表单快照。


## 官方请求规模接口与当前显示规则

官方 SDK Client.estimate_costs(collection_id, request) 调用 Process.estimate_costs：POST /api/retrieve/v1/processes/{id}/costing，JSON 为 {"inputs": request}。本机官方响应提供 id=size、cost、limit，没有文件字节数。官方前端 useBarProgress 使用 100 * cost / limit 画进度条；没有上限或上限为零时不计算百分比，超过上限标记超限。不能把规模值直接命名为 bytes、MB 或 GB。

依据：[官方前端规模进度条实现](https://cds.climate.copernicus.eu/_next/static/chunks/pages/datasets/%5Bslug%5D-46e59690ce9e2eb5.js)、本地安装的 ecmwf.datastores processing.py 中 estimate_costs。官方资料同时说明不同数据集存在字段数及体积限制：[CDS documentation](https://confluence.ecmwf.int/pages/viewpage.action?pageId=278541744)。本项目只显示接口实际提供的规模与上限，不自行假设固定单位或所有数据集上限相同。

Web 默认 CDS；右列保留单一 AI 输入、手动请求规模估算、只读预览。仅刷新按钮查询 costing，字段修改不自动估算；请求变化后旧结果明确标记过期，输出目录不影响规模。日期拆分显示整个选择的总规模，单次上限需由每个实际子任务满足。估算只读，复用同一编译器及定义版本核对，不执行 retrieve。

2026-10-27 定向证据：14 项后端测试覆盖官方 SDK 转发、零值/超限/未知上限、失败脱敏及版本/参数一致性；26 组模拟服务的 Playwright 功能检查覆盖逗号输入、类型、AI 回填撤销、手动估算调用次数和过期结果，页面错误为零。真实运行实例估算 ERA5 single levels 的 2024-01-01 00:00、2m_temperature 小请求返回 online、cost=1、limit=121000，任务和运行 Worker 均为零。



## 请求工作区呈现规则

数据集下拉在未编辑时显示目录标题，编辑时使用真实 ID；唯一名称搜索结果可以按 Enter 选择，目录状态与 ID 独立为辅助行。工具栏与选择框在宽屏同排，窄屏换行。

枚举类型取自元数据；少于 5 项的多选直接显示勾选卡片，不提供文字输入，分类和时间字段同样适用。其他非变量多选提供直接输入及完整分类浏览，分类视口限制高度，不删候选。明确命名的 year、years、month、months、day、days、time、times、hour、hours 只作可选排版分组，不推断 ERA5 字段、默认值或 wire 编码；不匹配的字段沿用通用控件。时间字段统一为两列；达到 5 项的多选由受控组合输入框提供同宽下拉，输入或聚焦展开，支持按钮、外部点击及 Esc 关闭。帮助使用可展开提示；本地输出目录与浏览已按 DRAFT-7 移除；拆分方式、提交请求和返回队列在右栏的请求拆分与提交卡片内，仍使用同一原生表单与唯一提交入口，提交中禁用、失败反馈与重试仍可用。JSON 预览仅压缩短的原始类型数组显示，解析结果仍与请求 payload 一致。

2026-10-27 用户要求对照设计预览纠正界面差异，已通过真实页面截图与设计参考对照，并做 27 组针对性检查；生产任务仍为零。修复 HTML 入口长期缓存，两个入口路径的 no-cache 定向测试通过。截图和工具中间文件不作为项目快照保留。


## 变量搜索、时间组合输入与地图参考

变量选择只来自候选勾选/批选；少于 5 项时直接勾选，其余提供纯搜索，不支持文字直接选入。标签区常驻，默认一行，完整展示全部标签并自然换行增高，清空恢复一行；候选视口为 560px，不截断分类或候选。其他枚举与时间在适用输入控件时仍支持严格名称/ID 输入。时间组合框独立维护展开状态，输入文本不再强制展开无法关闭；完整 CSV 按 Enter 替换该字段，保留原始字符串、数值、布尔类型，非法值不回填。

参考地图数据：[Natural Earth ne_110m_land.geojson](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson)，[许可](https://www.naturalearthdata.com/about/terms-of-use/)为 public domain。原始数据 138160 bytes，转换为项目内运行资产 world-land.json 的 127 条轮廓路径，坐标保留两位小数，约 68KB；是离线底图资产而非历史快照。以经纬度的 Plate carrée 投影显示，纬度向上，WGS84 经纬输入不变，只有 SVG 的 y 轴反向。经度作显示归一化，跨日界线使用重复世界与裁切；标记与选择框共享坐标系。地图固定为世界范围，不再提供世界/定位模式切换；区域选择框与点标记仍跟随坐标，不修改请求、数据库或文件。地图提供粗略位置上下文，精细空间精度与请求是否可用仍由原字段约束和数据源决定。

37 组功能检查覆盖候选高度/常驻标签、变量 Enter 不选入、候选勾选、时间两列/同宽/按钮关闭/外部关闭/Esc/焦点、CSV 替换与 01/0/false 保真、真实预览、地图区域/点位/日界线/无效草稿、0° 坐标与窄屏；生产任务为零。正常 ERA5 定义及本地预览为真实接口，constraints 和补充类型元数据使用模拟；地图不请求在线瓦片。未进行本次未要求的截图检查。



2026-10-27 本轮修订的 29 项定向交互断言、TypeScript/Vite 构建和差异检查通过。检查使用真实 ERA5 字段、后端目录浏览和按月预览；约束、少量选项样例及创建响应采用隔离模拟，覆盖提交中禁用、参数一致性、失败重试与成功导航。生产任务为零、无自动 costing 或页面运行错误；本轮未截图或执行无关全量测试。



## 请求与链接路线更新

2026-10-28：DRAFT-7 已获用户批准。保留字段选择、编码、AI、手动规模与请求拆分；移除本地目录、文件输出和 ARCO 子集导出。CDS 只提交并查询结果元数据；两个 NCAR 只列目录并查询响应头、返回文件链接。此前说明中的本地下载/输出规则由本条覆盖；字段与地图规则仍有效。TASK-32 记录 148 项相关后端测试、25 项功能检查及真实三来源链接证据；没有下载数据文件。
