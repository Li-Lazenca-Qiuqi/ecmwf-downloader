"""
创建任务页面视图

负责 UI 结构定义和组件组合。
"""

from typing import Any, Dict, Iterable, List, Literal

from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.events import Key
from textual.widget import Widget
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from src.ui.dialogs import RequestPreviewDialog
from src.ui.widgets.dynamic_form_field import (
    DynamicFieldWidget,
    DynamicFormFieldsContainer,
)

from .controller import CreateTaskController
from .services import SchemaLoadResult


class CreateTaskView(Widget):
    """创建任务页面视图

    职责：
    - UI 结构定义（compose）
    - CSS 样式
    - 组件组合
    - 将用户事件委托给 Controller
    """

    DEFAULT_CSS = """
    CreateTaskView {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
    }

    #config-container {
        width: 1fr;
        height: auto;
        max-height: 100%;
        layout: vertical;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 1 2;
    }

    CreateTaskView Input {
        width: 1fr;
        height: auto;
        min-height: 1;
        border: round $panel;
        background: transparent;
        color: $text;
    }

    CreateTaskView Input:focus {
        border: round $accent;
    }

    #config-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 2;
    }

    .form-label {
        text-style: bold;
        margin-bottom: 0;
        color: $text 80%;
    }

    .form-section {
        height: auto;
        margin-bottom: 1;
    }

    #actions-section {
        height: auto;
        margin: 1 3 0 3;
        padding: 0 1;
    }

    #actions-section Button {
        width: 1fr;
    }

    #split-strategy-set {
        height: auto;
    }

    #dataset-section {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: round $panel;
    }

    .dataset-input-row {
        height: auto;
        align: center middle;
    }

    #schema-status {
        margin-top: 0;
        color: $text-muted;
    }

    #schema-status.loading {
        color: $warning;
    }

    #schema-status.success {
        color: $success;
    }

    #schema-status.error {
        color: $error;
    }

    #dynamic-form-section {
        height: auto;
        margin-top: 1;
        padding-top: 1;
        border-top: solid $panel;
    }

    #dynamic-fields {
        height: auto;
    }

    #static-options-section {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $panel;
    }

    #btn-load-schema, #btn-save-config, #btn-load-config, #btn-ai-generate {
        width: auto;
        min-width: 0;
        padding: 0 1;
    }
    """

    def __init__(self, app, **kwargs):
        """初始化创建任务视图

        Args:
            app: 应用实例引用
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._app_ref = app

        # 创建控制器
        self._controller = CreateTaskController(self, app)

        # 设置控制器回调
        self._controller.on_schema_loaded = self._on_schema_loaded
        self._controller.on_fields_rendered = self._on_fields_rendered
        self._controller.on_config_loaded = self._on_config_loaded
        self._controller.on_ai_result_applied = self._on_ai_result_applied
        self._controller.on_status_changed = self._update_schema_status
        self._controller.on_notify = self._show_notify

        # 待恢复的字段值
        self._pending_field_values: Dict[str, List[Any]] = {}

    @property
    def controller(self) -> CreateTaskController:
        """获取控制器实例"""
        return self._controller

    def compose(self) -> Iterable:
        """构建创建任务 UI"""
        with ScrollableContainer(id="config-container", classes="content-container"):
            # 标题
            yield Label("创建下载任务", id="config-title", classes="page-title")

            # 数据集 ID 输入区域
            with Vertical(id="dataset-section", classes="form-section"):
                yield Label("数据集 ID", classes="form-label")
                with Horizontal(classes="dataset-input-row"):
                    yield Input(
                        placeholder="输入数据集 ID",
                        id="input-dataset",
                        value="",
                    )
                    yield Button("在线加载", id="btn-load-schema", variant="primary")
                    yield Button("保存", id="btn-save-config", variant="default")
                    yield Button("读取", id="btn-load-config", variant="default")
                    yield Button("AI生成", id="btn-ai-generate", variant="default")
                yield Label("输入数据集 ID 后点击加载", id="schema-status")

            # 动态表单区域
            with Vertical(id="dynamic-form-section", classes="form-section"):
                yield Label("数据集参数", classes="form-label")
                yield DynamicFormFieldsContainer(id="dynamic-fields")

            # 静态配置选项
            with Vertical(id="static-options-section", classes="form-section"):
                # 输出目录
                with Vertical(classes="form-section"):
                    yield Label("输出目录", classes="form-label")
                    yield Input(
                        placeholder="./data/downloads",
                        id="input-output",
                        value="./data/downloads",
                    )

                # 拆分策略配置
                with Vertical(classes="form-section"):
                    yield Label("拆分策略", classes="form-label")
                    with RadioSet(id="split-strategy-set"):
                        yield RadioButton("按月", id="strategy-month", value=True)
                        yield RadioButton("按年", id="strategy-year")
                        yield RadioButton("不拆分", id="strategy-none")

            # 操作按钮
            with Horizontal(id="actions-section"):
                yield Button("预览", id="btn-preview", variant="primary")
                yield Button("创建任务", id="btn-create", variant="default")
                yield Button("清空参数", id="btn-clear", variant="default")
                yield Button("重置", id="btn-reset", variant="default")

    # ==================== 事件处理 ====================

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理"""
        button_id = event.button.id

        if button_id == "btn-load-schema":
            dataset_id = self.query_one("#input-dataset", Input).value.strip()
            load_button = self.query_one("#btn-load-schema", Button)
            load_button.disabled = True
            try:
                await self._controller.handle_load_schema(dataset_id)
            finally:
                load_button.disabled = self._controller.is_loading

        elif button_id == "btn-save-config":
            self._controller.handle_save_config(
                self.query_one("#input-dataset", Input).value.strip(),
                self.query_one("#input-output", Input).value.strip(),
                self._get_split_strategy(),
            )

        elif button_id == "btn-load-config":
            self._controller.handle_load_config()

        elif button_id == "btn-ai-generate":
            self._controller.handle_ai_generate()

        elif button_id == "btn-preview":
            await self._handle_preview()

        elif button_id == "btn-create":
            self._handle_create()

        elif button_id == "btn-clear":
            self._handle_clear()

        elif button_id == "btn-reset":
            self._handle_reset()

    def on_dynamic_field_widget_field_changed(
        self,
        event: DynamicFieldWidget.FieldChanged,
    ) -> None:
        """处理动态字段值变化事件"""
        container = self.query_one("#dynamic-fields", DynamicFormFieldsContainer)
        self._controller.handle_field_changed(
            event.field_name,
            event.selected_values,
            container,
        )

    def on_key(self, event: Key) -> None:
        """处理键盘事件"""
        if event.key == "enter":
            focused = self.app.focused
            if focused and isinstance(focused, Button):
                focused.action_press()
                event.stop()

    def on_unmount(self) -> None:
        """组件卸载时清理"""
        pass

    # ==================== 业务逻辑处理 ====================

    async def _handle_preview(self) -> None:
        """处理预览按钮"""
        try:
            config = self._controller.build_download_config(
                self.query_one("#input-dataset", Input).value.strip(),
                self.query_one("#input-output", Input).value.strip(),
            )
            split_strategy = self._get_split_strategy()
            preview_items = self._controller.preview_tasks(config, split_strategy)

            def do_create():
                self._handle_create()

            self.app.push_screen(
                RequestPreviewDialog(preview_items, split_strategy, callback=do_create)
            )

        except ValueError as e:
            error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
            self.notify(f"参数验证失败: {error_msg}", severity="error")
        except Exception as e:
            error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
            self.notify(f"预览失败: {error_msg}", severity="error")

    def _handle_create(self) -> None:
        """处理创建任务按钮"""
        try:
            config = self._controller.build_download_config(
                self.query_one("#input-dataset", Input).value.strip(),
                self.query_one("#input-output", Input).value.strip(),
            )
            split_strategy = self._get_split_strategy()
            task_ids = self._controller.create_tasks(config, split_strategy)
            self.notify(f"已创建 {len(task_ids)} 个任务", severity="success")
            self._handle_clear()

        except ValueError as e:
            error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
            self.notify(f"参数验证失败: {error_msg}", severity="error")
        except Exception as e:
            error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
            self.notify(f"创建任务失败: {error_msg}", severity="error")

    def _handle_clear(self) -> None:
        """清空表单"""
        self.query_one("#input-dataset", Input).value = ""
        self._update_schema_status("输入数据集 ID 后点击加载", "")

        if self._controller.is_schema_loaded:
            container = self.query_one("#dynamic-fields", DynamicFormFieldsContainer)
            container.clear_all()

        self.query_one("#input-output", Input).value = ""

    def _handle_reset(self) -> None:
        """重置表单"""
        self.query_one("#input-dataset", Input).value = ""
        self._update_schema_status("输入数据集 ID 后点击加载", "")

        self._controller.reset_form_state()

        container = self.query_one("#dynamic-fields", DynamicFormFieldsContainer)
        for child in list(container.children):
            child.remove()

        self.query_one("#input-output", Input).value = "./data/downloads"

        strategy_set = self.query_one("#split-strategy-set", RadioSet)
        buttons = list(strategy_set.query(RadioButton))
        for i, btn in enumerate(buttons):
            btn.value = (i == 0)

    def _get_split_strategy(self) -> Literal["month", "year", "none"]:
        """获取当前选中的拆分策略"""
        radio_set = self.query_one("#split-strategy-set", RadioSet)
        pressed = radio_set.pressed_button
        if pressed is None:
            return "month"

        if pressed.id == "strategy-year":
            return "year"
        if pressed.id == "strategy-none":
            return "none"
        return "month"

    # ==================== 控制器回调 ====================

    def _on_schema_loaded(self, result: SchemaLoadResult) -> None:
        """Schema 加载完成回调"""
        self._render_dynamic_fields()

    def _on_fields_rendered(self) -> None:
        """字段渲染回调（从配置文件加载时）"""
        self._render_dynamic_fields()

    def _on_config_loaded(self, dataset: str, output_dir: str, strategy: str) -> None:
        """配置加载完成回调，恢复静态字段

        Args:
            dataset: 数据集 ID
            output_dir: 输出目录
            strategy: 拆分策略
        """
        # 恢复数据集 ID
        if dataset:
            self.query_one("#input-dataset", Input).value = dataset

        # 恢复输出目录
        if output_dir:
            self.query_one("#input-output", Input).value = output_dir

        # 恢复拆分策略
        strategy_set = self.query_one("#split-strategy-set", RadioSet)
        buttons = list(strategy_set.query(RadioButton))
        strategy_map = {"month": 0, "year": 1, "none": 2}
        target_index = strategy_map.get(strategy, 0)
        for i, btn in enumerate(buttons):
            btn.value = (i == target_index)

    def _on_ai_result_applied(self, result: Dict[str, Any]) -> None:
        """AI 生成结果应用回调，更新 UI 控件

        Args:
            result: AI 生成的字段配置字典
        """
        container = self.query_one("#dynamic-fields", DynamicFormFieldsContainer)

        for field_name, field_info in result.items():
            if field_name not in self._controller.form_state.fields:
                continue

            selected = field_info.get("selected", [])
            if not selected:
                continue

            # 更新 UI 控件
            widget = container.get_field_widget(field_name)
            if widget:
                widget.set_selected_values(selected)

    # ==================== UI 更新方法 ====================

    def _render_dynamic_fields(self) -> None:
        """渲染动态表单字段"""
        try:
            container = self.query_one("#dynamic-fields", DynamicFormFieldsContainer)
            if container is None:
                raise RuntimeError("找不到 dynamic-fields 容器")

            form_state = self._controller.form_state
            if not form_state.fields:
                self.notify("警告：数据集没有可用的字段", severity="warning")
                return

            # 定义挂载完成后的回调
            def on_fields_mounted():
                """字段挂载完成后的回调"""
                # 恢复从配置文件加载的字段值
                if self._pending_field_values:
                    for field_name, values in self._pending_field_values.items():
                        if field_name in form_state.fields:
                            form_state.set_field_selection(field_name, values)
                            widget = container.get_field_widget(field_name)
                            if widget:
                                widget.set_selected_values(values)
                    self._pending_field_values = {}

                # 初始化 area_group 相关字段的显示状态
                area_group = form_state.fields.get("area_group")
                if area_group and area_group.selected:
                    mode = str(area_group.selected[0]).strip().lower()
                    global_widget = container.get_field_widget("global")
                    area_widget = container.get_field_widget("area")

                    if mode == "global":
                        if global_widget:
                            global_widget.display = False
                        if area_widget:
                            area_widget.display = False
                    elif mode == "area":
                        if global_widget:
                            global_widget.display = False

                container.refresh(layout=True)
                self.refresh(layout=True)

            container.render_fields(form_state.fields, on_complete=on_fields_mounted)

        except Exception as e:
            self.notify(f"渲染字段失败: {str(e)}", severity="error")
            raise

    def _update_schema_status(self, message: str, status_type: str = "") -> None:
        """更新 Schema 加载状态显示"""
        status_label = self.query_one("#schema-status", Label)
        status_label.update(message)

        status_label.remove_class("loading", "success", "error")
        if status_type:
            status_label.add_class(status_type)

    def _show_notify(self, message: str, severity: str, timeout: int = 5) -> None:
        """显示通知"""
        self.notify(message, severity=severity, timeout=timeout)

    def refresh_data(self) -> None:
        """刷新数据接口。"""
        pass
