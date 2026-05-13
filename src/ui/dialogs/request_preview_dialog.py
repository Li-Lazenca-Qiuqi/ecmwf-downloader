"""
ECMWF Downloader TUI 请求预览对话框模块

展示任务拆分结果、预估大小和 Python 代码示例，支持用户在创建任务前进行确认。
"""

import json
from typing import Any, Callable, Dict, Iterable, List, Optional

from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Label, Static

from src.ui.dialogs.base_dialog import BaseDialog


class RequestPreviewDialog(BaseDialog):
    """请求预览对话框

    展示下载请求的详细参数、任务列表和 Python 代码示例，支持用户确认或取消。
    """

    DEFAULT_CSS = """
    RequestPreviewDialog {
        align: center middle;
    }

    RequestPreviewDialog > Container {
        width: 95;
        min-width: 70;
        height: 85%;
        min-height: 18;
        max-height: 36;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        layout: vertical;
    }

    RequestPreviewDialog .dialog-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    RequestPreviewDialog #content-area {
        height: 1fr;
        margin-bottom: 1;
    }

    RequestPreviewDialog #summary-area,
    RequestPreviewDialog #task-list-area,
    RequestPreviewDialog #code-area {
        height: auto;
        margin-bottom: 1;
    }

    RequestPreviewDialog #summary-area {
        padding: 1;
        background: transparent;
    }

    RequestPreviewDialog #summary-area Label {
        margin-bottom: 0;
    }

    RequestPreviewDialog .section-title {
        text-style: bold;
        margin-bottom: 0;
        color: $text;
    }

    RequestPreviewDialog #task-list-content,
    RequestPreviewDialog #code-content {
        width: 1fr;
        padding: 0 1;
    }

    RequestPreviewDialog #code-content {
        background: transparent;
    }

    RequestPreviewDialog .dialog-actions {
        align: center middle;
        height: auto;
        margin-top: 0;
    }
    """

    def __init__(
        self,
        preview_items: List[Dict[str, Any]],
        split_strategy: str = "month",
        callback: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        """初始化对话框。

        Args:
            preview_items: TaskService.preview_tasks() 返回的预览列表。
            split_strategy: 拆分策略名称（month/year/none）。
            callback: 确认回调函数，无参数无返回值。
            **kwargs: 传递给父类的参数。
        """
        super().__init__(title="请求预览", **kwargs)
        self._preview_items: List[Dict[str, Any]] = preview_items
        self._split_strategy: str = split_strategy
        self._callback = callback

    def compose(self) -> Iterable:
        """构建对话框 UI。"""
        task_list_text = self._generate_task_list_text()
        first_item = self._preview_items[0] if self._preview_items else {}
        request_text = self._generate_request_code(first_item)

        with Container(classes="dialog-container"):
            yield Label(self._title, classes="dialog-title")

            with VerticalScroll(id="content-area"):
                # 汇总区域
                with Container(id="summary-area"):
                    yield Label(
                        f"拆分策略: {self._format_split_strategy(self._split_strategy)}"
                    )
                    yield Label(
                        f"任务数量: [bold]{len(self._preview_items)}[/bold] 个"
                    )
                    yield Label(
                        f"预估总大小: [bold]{self._estimate_total_size()}[/bold]"
                    )

                # 任务列表区域
                with Container(id="task-list-area"):
                    yield Label("任务列表:", classes="section-title")
                    yield Static(task_list_text, id="task-list-content")

                # 请求代码区域
                with Container(id="code-area"):
                    yield Label("第一个请求参数:", classes="section-title")
                    yield Static(request_text, id="code-content")

            # 操作按钮
            with Horizontal(classes="dialog-actions"):
                yield Button("确认创建", id="btn-confirm", variant="primary")
                yield Button("取消", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        """挂载后设置默认焦点到内容区域，便于键盘滚动。"""
        try:
            self.query_one("#content-area", VerticalScroll).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件。"""
        button_id = event.button.id
        if button_id == "btn-confirm":
            self._handle_confirm()
        elif button_id == "btn-cancel":
            self._handle_cancel()

    def _handle_confirm(self) -> None:
        """处理确认操作。"""
        if self._callback:
            try:
                self._callback()
            except Exception:
                # 回调异常时记录日志，但仍关闭对话框
                # 上层应有自己的错误处理和用户提示
                self.log.exception("预览对话框回调执行失败")
        self.dismiss()

    def _handle_cancel(self) -> None:
        """处理取消操作。"""
        self.dismiss()

    def get_form_data(self) -> Optional[Dict[str, Any]]:
        """收集表单数据。

        注意：此方法仅为基类抽象契约兼容而保留。
        实际确认逻辑已通过 callback 参数实现，主流程不再依赖此返回值。
        """
        return {"confirmed": True}

    @staticmethod
    def _format_split_strategy(split_strategy: str) -> str:
        """格式化拆分策略显示文本。"""
        mapping = {
            "month": "按月",
            "year": "按年",
            "none": "不拆分",
        }
        return mapping.get(split_strategy, split_strategy)

    def _generate_task_list_text(self) -> str:
        """生成任务列表的文本内容。"""
        if not self._preview_items:
            return "无可创建任务，请检查请求参数。"

        lines = []
        for index, item in enumerate(self._preview_items, start=1):
            time_range = self._format_time_range(item.get("time_range", {}))
            size_estimate = self._estimate_task_size(item)
            lines.append(
                f"[bold]任务 {index}[/bold] - {time_range}  [dim]({size_estimate})[/dim]"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_time_range(time_range: Dict[str, Any]) -> str:
        """格式化时间范围展示文本。"""
        years = [str(year) for year in time_range.get("years", [])]
        months = [f"{int(month):02d}" for month in time_range.get("months", [])]
        days_raw = time_range.get("days", [])
        days = [f"{int(day):02d}" for day in days_raw] if days_raw else []

        year_text = ",".join(years) if years else "-"
        month_text = ",".join(months) if months else "-"
        day_text = ",".join(days) if days else "全月"
        return f"{year_text}-{month_text} ({day_text})"

    def _estimate_task_size(self, item: Dict[str, Any]) -> str:
        """估算单个任务的数据大小。"""
        api_params = item.get("api_params", {})

        # 获取变量数量
        variables = api_params.get("variable", [])
        var_count = len(variables) if isinstance(variables, list) else 1

        # 获取气压层数量
        pressure_levels = api_params.get("pressure_level", [])
        level_count = len(pressure_levels) if isinstance(pressure_levels, list) else 1
        if level_count == 0:
            level_count = 1

        # 获取时间点数量
        times = api_params.get("time", [])
        time_count = len(times) if isinstance(times, list) else 4
        if time_count == 0:
            time_count = 4

        # 获取天数
        time_range = item.get("time_range", {})
        days = time_range.get("days", [])
        day_count = len(days) if days else 30

        # 估算大小
        base_size_mb = 0.1
        area = api_params.get("area")
        if area:
            base_size_mb *= 0.1

        total_size_mb = base_size_mb * var_count * level_count * time_count * day_count

        if total_size_mb < 1:
            return f"约 {total_size_mb * 1000:.0f} KB"
        elif total_size_mb < 1024:
            return f"约 {total_size_mb:.1f} MB"
        else:
            return f"约 {total_size_mb / 1024:.2f} GB"

    def _estimate_total_size(self) -> str:
        """估算所有任务的总大小。"""
        if not self._preview_items:
            return "0 MB"

        total_mb = 0.0
        for item in self._preview_items:
            size_str = self._estimate_task_size(item)
            if "KB" in size_str:
                total_mb += (
                    float(size_str.replace("约 ", "").replace(" KB", "")) / 1000
                )
            elif "GB" in size_str:
                total_mb += (
                    float(size_str.replace("约 ", "").replace(" GB", "")) * 1024
                )
            elif "MB" in size_str:
                total_mb += float(size_str.replace("约 ", "").replace(" MB", ""))

        if total_mb < 1:
            return f"{total_mb * 1000:.0f} KB"
        elif total_mb < 1024:
            return f"{total_mb:.1f} MB"
        else:
            return f"{total_mb / 1024:.2f} GB"

    def _generate_request_code(self, item: Dict[str, Any]) -> str:
        """生成请求参数代码（仅 request 字典部分）。"""
        if not item:
            return "# 无任务"

        dataset = item.get("dataset", "unknown-dataset")
        api_params = item.get("api_params", {})

        # 构建 request 字典
        request_lines = [f'dataset = "{dataset}"', "", "request = {"]
        for key, value in api_params.items():
            if value is None:
                continue
            if isinstance(value, list):
                formatted_list = ", ".join(f'"{v}"' for v in value)
                request_lines.append(f'    "{key}": [{formatted_list}],')
            elif isinstance(value, str):
                request_lines.append(f'    "{key}": "{value}",')
            else:
                request_lines.append(f'    "{key}": {value},')
        request_lines.append("}")

        return "\n".join(request_lines)
