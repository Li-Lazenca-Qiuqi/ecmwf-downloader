"""
创建任务页面模块

提供基于数据集 Schema 的动态配置表单，支持：
- 从 ecmwf-datastores-client 获取数据集字段定义
- 约束驱动的字段更新（如选择年份后自动更新可选日期）
- 创建新的下载任务
"""

from .view import CreateTaskView
from .controller import CreateTaskController

__all__ = ["CreateTaskView", "CreateTaskController"]
