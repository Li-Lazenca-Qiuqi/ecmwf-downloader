# -*- coding: utf-8 -*-
"""
动态表单字段组件

提供可复用的动态表单字段，支持多种输入类型和约束更新。
"""

from typing import Any, Dict, List, Optional

from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Checkbox, Input, Label, RadioButton, RadioSet, Select, Static, Switch

from src.core.dataset_schema import DynamicFormField, FieldType


class DynamicFieldWidget(Vertical):
    """动态表单字段组件

    根据字段类型渲染不同的输入控件：
    - STRING_ARRAY: Input（逗号分隔多选）
    - STRING_SINGLE: Select 下拉框
    - INTEGER_ARRAY: Input（数字列表）
    - INTEGER_SINGLE: Input（单数字）
    - FLOAT_ARRAY: Input（浮点数列表）

    特性：
    - 支持加载状态显示
    - 发送 FieldChanged 消息通知父组件
    - 支持外部更新可选值
    """
    QUICK_SELECT_PROMPT_VALUE = "__quick_select_prompt__"

    DEFAULT_CSS = """
    DynamicFieldWidget {
        height: auto;
        margin-bottom: 1;
    }

    .field-label {
        text-style: bold;
        margin-bottom: 0;
        color: $text 80%;
        height: auto;
    }

    .field-required {
        color: $error;
    }

    .field-input {
        width: 1fr;
        height: 3;
        min-height: 3;
        border: round $panel;
        background: transparent;
        color: $text;
    }

    .field-input:focus {
        border: round $accent;
    }

    .field-select {
        width: 1fr;
        height: auto;
        min-height: 3;
        margin-top: 0;
        border: round $panel;
        background: transparent;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }

    .field-select:focus {
        border: round $panel;
        background: transparent;
    }

    .field-select-quick {
        width: 1fr;
        height: auto;
        min-height: 3;
        margin-top: 0;
        margin-left: 0;
        border: round $panel;
        background: transparent;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }

    .field-select-quick:focus {
        border: round $panel;
        background: transparent;
    }

    .field-hint {
        color: $text-muted;
        text-style: italic;
        margin-top: 0;
        height: auto;
    }

    .field-loading {
        color: $warning;
        text-style: italic;
    }

    .field-count {
        color: $accent;
        margin-left: 1;
    }

    .field-extent-row {
        height: auto;
    }

    .field-extent {
        width: 1fr;
        height: 3;
    }

    .field-radio-set {
        height: auto;
    }

    .field-switch {
        height: auto;
    }
    """

    class FieldChanged(Message):
        """字段值变化消息

        当用户修改字段值时发送，通知父组件更新约束。
        """

        def __init__(self, field_name: str, selected_values: List[Any]) -> None:
            """初始化消息

            Args:
                field_name: 字段名称
                selected_values: 选中的值列表
            """
            super().__init__()
            self.field_name = field_name
            self.selected_values = selected_values

    def __init__(
        self,
        field: DynamicFormField,
        *,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        """初始化动态字段组件

        Args:
            field: 动态字段状态对象
            name: 组件名称
            id: 组件 ID
            classes: CSS 类名
            disabled: 是否禁用
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._field = field
        self._suppress_events = False
        self._updating_options = False  # 标记是否正在更新选项（用于忽略期间的事件）
        self._options_update_seq = 0  # 选项更新序号（用于延迟释放更新标记）
        self._input_widget: Optional[Input] = None
        self._select_widget: Optional[Select] = None
        self._switch_widget: Optional[Switch] = None
        self._radio_set_widget: Optional[RadioSet] = None
        self._licence_checkboxes: Dict[str, Checkbox] = {}
        self._extent_inputs: Dict[str, Input] = {}

    def compose(self) -> None:
        """构建字段 UI"""
        # 标签行
        label_text = self._field.label
        if self._field.required:
            label_text += " *"

        # 显示可选值数量
        if self._field.values:
            count_text = f"({len(self._field.values)} 可选)"
            label_text += f"  {count_text}"

        yield Label(label_text, classes="field-label")

        # 根据字段类型渲染输入控件
        field_type = self._field.field_type

        if field_type == FieldType.STRING_SINGLE:
            # 单选下拉框
            yield from self._compose_select()
        elif field_type == FieldType.BOOLEAN:
            yield from self._compose_switch()
        elif field_type == FieldType.EXCLUSIVE_GROUP:
            yield from self._compose_exclusive_group()
        elif field_type == FieldType.GEO_EXTENT:
            yield from self._compose_geo_extent()
        elif field_type == FieldType.LICENCE:
            yield from self._compose_licences()
        else:
            # 默认使用输入框
            yield from self._compose_input()

        # 提示信息
        hint = self._get_field_hint()
        if hint:
            yield Label(hint, classes="field-hint")

    def _compose_input(self) -> None:
        """构建输入框控件（带下拉选择的组合控件）

        对于有可选值的字段，同时显示：
        - Input 输入框：显示当前选择，支持手动输入
        - Select 下拉框：快速选择可选项（在输入框下方）
        """
        placeholder = self._get_placeholder()
        initial_value = self._format_selected_for_input()
        quick_options = self._build_quick_select_options() if self._field.values else []

        self._input_widget = Input(
            placeholder=placeholder,
            value=initial_value,
            id=f"input-{self._field.name}",
            classes="field-input",
        )
        yield self._input_widget

        # 如果有可选值，在输入框下方显示快速选择
        if quick_options:
            self._select_widget = Select(
                options=quick_options,
                value=self.QUICK_SELECT_PROMPT_VALUE,
                id=f"select-{self._field.name}",
                classes="field-select-quick",
                allow_blank=False,
            )
            yield self._select_widget

    def _compose_select(self) -> None:
        """构建下拉选择框控件"""
        options = self._build_select_options()
        allow_blank = not self._field.required

        # Textual 7.5+：Select 的 value 不能为 None；未选择时应使用 Select.BLANK。
        # 对于必填字段，如果当前没有选中值且存在可选项，则默认选择第一项，避免组件挂载时报错。
        if self._field.selected:
            initial_value = str(self._field.selected[0])
        elif options and not allow_blank:
            initial_value = str(options[0][1])
            self._field.set_selected([initial_value])
        else:
            initial_value = Select.BLANK

        # 防御：如果没有任何可选项，允许空值以避免 Select 在挂载阶段访问 options[0]。
        if not options:
            allow_blank = True
            initial_value = Select.BLANK

        self._select_widget = Select(
            options=options,
            value=initial_value,
            id=f"select-{self._field.name}",
            classes="field-select",
            allow_blank=allow_blank,
        )
        # 明确恢复为旧版可见高度，避免外层样式覆盖导致文字被裁切
        self._select_widget.styles.height = "auto"
        self._select_widget.styles.min_height = 3
        yield self._select_widget

    def _compose_switch(self) -> None:
        """构建布尔开关控件（Switch）"""
        initial = bool(self._field.selected) and str(self._field.selected[0]).strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )
        self._switch_widget = Switch(
            value=initial,
            id=f"switch-{self._field.name}",
            classes="field-switch",
        )
        yield self._switch_widget

        # FreeEditionWidget 通常会携带解释文本，放在开关下方辅助理解
        details = self._field.definition.details.get("details", {})
        text = details.get("text")
        if isinstance(text, str) and text.strip():
            yield Static(text.strip(), classes="field-hint")

    def _compose_exclusive_group(self) -> None:
        """构建排他分组控件（RadioSet）"""
        options = self._get_exclusive_group_options()
        if not options:
            # 无法推断可选项时降级为自由输入，避免 UI 空白
            yield from self._compose_input()
            return

        selected_value = str(self._field.selected[0]) if self._field.selected else None
        buttons: List[RadioButton] = []
        for option in options:
            option_id = option.get("id", "")
            option_label = option.get("label", option_id)
            pressed = selected_value == option_id if selected_value is not None else False
            buttons.append(
                RadioButton(
                    label=option_label,
                    value=pressed,
                    name=option_id,
                    id=f"radio-{self._field.name}-{option_id}",
                    compact=False,
                )
            )

        self._radio_set_widget = RadioSet(
            *buttons,
            id=f"radio-set-{self._field.name}",
            classes="field-radio-set",
            compact=False,
        )
        yield self._radio_set_widget

    def _compose_geo_extent(self) -> None:
        """构建地理范围控件（4 个输入框：N, W, S, E）"""
        initial = self._get_geo_extent_initial_values()

        def _make_input(key: str, placeholder: str) -> Input:
            return Input(
                placeholder=placeholder,
                value=initial.get(key, ""),
                id=f"extent-{self._field.name}-{key}",
                classes="field-input field-extent",
            )

        self._extent_inputs = {
            "n": _make_input("n", "N"),
            "w": _make_input("w", "W"),
            "s": _make_input("s", "S"),
            "e": _make_input("e", "E"),
        }

        # 直接 yield Horizontal 容器，避免使用 with 语句
        yield Horizontal(
            self._extent_inputs["n"],
            self._extent_inputs["w"],
            self._extent_inputs["s"],
            self._extent_inputs["e"],
            classes="field-extent-row",
        )

    def _compose_licences(self) -> None:
        """构建许可证控件（Checkbox 列表）"""
        details = self._field.definition.details.get("details", {})
        licences = details.get("licences", [])
        if not isinstance(licences, list) or not licences:
            # 无法解析许可证列表时降级为自由输入
            yield from self._compose_input()
            return

        self._licence_checkboxes = {}
        selected_ids = {str(v) for v in self._field.selected}

        for lic in licences:
            if not isinstance(lic, dict):
                continue
            lic_id = lic.get("id")
            if not lic_id:
                continue
            lic_id = str(lic_id)
            lic_label = str(lic.get("label") or lic_id)
            checkbox = Checkbox(
                label=lic_label,
                value=lic_id in selected_ids,
                name=lic_id,
                id=f"licence-{self._field.name}-{lic_id}",
                compact=True,
            )
            self._licence_checkboxes[lic_id] = checkbox
            yield checkbox

    def _build_select_options(self) -> List[tuple]:
        """构建下拉框选项列表（已排序）

        Returns:
            List[tuple]: (显示文本, 值) 元组列表
        """
        # 使用智能排序
        sorted_values = self._smart_sort_values(list(self._field.values))
        options = [(str(value), str(value)) for value in sorted_values]
        return options

    def _build_select_options_with_toggle(self) -> List[tuple]:
        """构建带切换标记的下拉框选项列表

        已选中的值显示 `-`，未选中的值显示 `+`
        保持原始排序顺序

        Returns:
            List[tuple]: (显示文本, 值) 元组列表
        """
        # 获取当前选中的值
        current_values = set(self._field.selected) if self._field.selected else set()

        options = []
        # 使用智能排序（数字按数值，字符串按字母）
        sorted_values = self._smart_sort_values(list(self._field.values))
        for value in sorted_values:
            value_str = str(value)
            # 已选中显示 `-`，未选中显示 `+`
            prefix = "-" if value_str in current_values else "+"
            options.append((f"{prefix} {value_str}", value_str))
        return options

    def _build_quick_select_options(self) -> List[tuple]:
        """构建快速选择按钮的选项列表（含占位项）。"""
        return [("select", self.QUICK_SELECT_PROMPT_VALUE), *self._build_select_options_with_toggle()]

    def _update_select_options(self) -> None:
        """更新下拉框选项，刷新 +/- 标记

        注意：Textual Select.set_options() 会重置值如果 label 变化。
        对“快速选择”场景不恢复当前值，避免二次触发 Select.Changed 导致选中反转。
        """
        if self._select_widget:
            seq = self._begin_options_update()
            try:
                # 构建新选项
                new_options = (
                    self._build_quick_select_options()
                    if self._input_widget is not None
                    else self._build_select_options_with_toggle()
                )
                self._select_widget.set_options(new_options)
            finally:
                self._end_options_update(seq)

    def _begin_options_update(self) -> int:
        """开始一次下拉选项更新并返回更新序号。"""
        self._options_update_seq += 1
        self._updating_options = True
        self._suppress_events = True
        return self._options_update_seq

    def _end_options_update(self, seq: int) -> None:
        """结束一次下拉选项更新。

        先立即恢复事件抑制标记，再延后一帧清除 updating 标记，
        以吸收 set_options 可能延后派发的 Select.Changed 事件。
        """
        self._suppress_events = False

        def _clear_updating_flag() -> None:
            if seq == self._options_update_seq:
                self._updating_options = False

        if self.is_mounted:
            self.call_after_refresh(_clear_updating_flag)
        else:
            _clear_updating_flag()

    def _get_placeholder(self) -> str:
        """获取输入框占位符

        Returns:
            str: 占位符文本
        """
        field_type = self._field.field_type

        if field_type == FieldType.INTEGER_ARRAY:
            return "逗号分隔的数字，如 500,850,1000"
        if field_type == FieldType.INTEGER_SINGLE:
            return "输入数字"
        if field_type == FieldType.FLOAT_ARRAY:
            return "逗号分隔的数字，如 90,-180,-90,180"
        if field_type == FieldType.STRING_ARRAY:
            if self._field.values:
                return f"逗号分隔，共 {len(self._field.values)} 可选"
            return "逗号分隔的值"
        return "输入值"

    def _get_field_hint(self) -> str:
        """获取字段提示信息

        Returns:
            str: 提示文本
        """
        # 根据字段名返回提示
        hints = {
            "variable": "选择要下载的气象变量",
            "year": "输入年份，如 2020,2021",
            "month": "输入月份 1-12",
            "day": "输入日期 1-31，留空表示全月",
            "time": "时间点，格式 HH:MM",
            "pressure_level": "气压层高度（hPa）",
            "area": "区域范围：N, W, S, E",
            "product_type": "数据产品类型",
        }
        return hints.get(self._field.name, "")

    def _format_selected_for_input(self) -> str:
        """格式化选中值为输入框显示格式

        对选中的值进行智能排序：
        - 数字类型按数值大小排序
        - 字符串类型按字母顺序排序
        - 混合类型：数字在前（按数值），字符串在后（按字母）

        Returns:
            str: 逗号分隔的字符串
        """
        if not self._field.selected:
            return ""

        # 智能排序选中的值
        sorted_values = self._smart_sort_values(self._field.selected)
        return ", ".join(str(v) for v in sorted_values)

    def _smart_sort_values(self, values: List[Any]) -> List[Any]:
        """智能排序值列表

        排序规则：
        - 纯数字：按数值大小排序
        - 纯字符串：按字母顺序排序
        - 混合：数字在前（按数值），字符串在后（按字母）

        Args:
            values: 待排序的值列表

        Returns:
            List[Any]: 排序后的值列表
        """
        if not values:
            return []

        # 尝试将所有值转换为数字
        numeric_values = []
        string_values = []

        for v in values:
            str_v = str(v)
            try:
                # 尝试转换为整数
                num = int(str_v)
                numeric_values.append((num, v))
            except ValueError:
                try:
                    # 尝试转换为浮点数
                    num = float(str_v)
                    numeric_values.append((num, v))
                except ValueError:
                    # 不是数字，作为字符串处理
                    string_values.append((str_v.lower(), v))

        # 按数值排序数字
        numeric_values.sort(key=lambda x: x[0])
        # 按字母排序字符串
        string_values.sort(key=lambda x: x[0])

        # 合并结果
        result = [v for _, v in numeric_values] + [v for _, v in string_values]
        return result

    def on_input_changed(self, event: Input.Changed) -> None:
        """输入框值变化事件处理

        Args:
            event: 输入变化事件
        """
        if self._suppress_events:
            return

        # 地理范围输入：由 4 个 Input 组成
        if self._extent_inputs and event.input in self._extent_inputs.values():
            values = self._parse_geo_extent_inputs()
            # 只有在 4 个值均有效时才触发更新，避免频繁清空导致约束抖动
            if values is not None:
                self.post_message(self.FieldChanged(self._field.name, values))
            return

        if event.input != self._input_widget:
            return

        # 解析输入值
        values = self._parse_input_value(event.value)

        # 发送消息
        self.post_message(self.FieldChanged(self._field.name, values))

    def on_select_changed(self, event: Select.Changed) -> None:
        """下拉框选择变化事件处理

        对于组合控件（Select + Input），选择下拉项时：
        - 将选中的值添加到输入框中（如果是多选字段）
        - 或替换输入框的值（如果是单选字段）
        """
        if self._suppress_events:
            return

        if event.select != self._select_widget:
            return

        # 如果正在更新选项，忽略所有事件（防止 set_options 触发的事件干扰）
        if self._updating_options:
            return

        # 获取选中的值
        value = event.value
        if value is None or value == Select.BLANK:
            return  # 选择空项时不做任何操作
        if value == self.QUICK_SELECT_PROMPT_VALUE:
            return
        value = str(value)

        # 纯单选 Select（无输入框）：
        # - 不走“+/- 快速多选”逻辑
        # - 不自动重开下拉，避免页面初始化后叠加多个下拉浮层
        # - 若值未变化则不重复发送事件，避免约束更新风暴
        if self._input_widget is None:
            if self._field.selected and str(self._field.selected[0]) == value:
                return
            self._field.set_selected([value])
            self.post_message(self.FieldChanged(self._field.name, [value]))
            return

        # 获取当前输入框中的值
        current_input = self._input_widget.value if self._input_widget else ""
        current_values = [v.strip() for v in current_input.split(",") if v.strip()]

        field_type = self._field.field_type
        is_multi_quick = field_type in (
            FieldType.STRING_ARRAY,
            FieldType.INTEGER_ARRAY,
            FieldType.FLOAT_ARRAY,
        )

        # 根据字段类型决定是添加、移除还是替换
        if field_type in (FieldType.STRING_ARRAY, FieldType.INTEGER_ARRAY, FieldType.FLOAT_ARRAY):
            # 多选字段：切换选中状态（已存在则移除，不存在则添加）
            if value in current_values:
                current_values.remove(value)
            else:
                current_values.append(value)
        else:
            # 单选字段：替换现有值
            current_values = [value]

        # 智能排序选中的值
        sorted_values = self._smart_sort_values(current_values)

        # 更新输入框
        new_input_value = ", ".join(str(v) for v in sorted_values)
        if self._input_widget:
            self._input_widget.value = new_input_value

        # 更新字段选中状态（用于更新 +/- 标记）
        self._field.set_selected(sorted_values)

        # 更新下拉框选项的 +/- 标记
        self._update_select_options()

        # 重置下拉框到占位项（显示 "select"），以允许重复选择同一项
        # 注意：此代码块只在 _input_widget 存在时执行（见上方 return 逻辑）
        self._suppress_events = True
        try:
            self._select_widget.value = self.QUICK_SELECT_PROMPT_VALUE
        finally:
            self._suppress_events = False

        # 快速多选模式：用户选择后自动再次展开，便于连续选择多个选项。
        if is_multi_quick and self._select_widget and self._select_widget.is_mounted:
            self.call_after_refresh(self._reopen_select)

        # 发送消息
        self.post_message(self.FieldChanged(self._field.name, sorted_values))

    def _reopen_select(self) -> None:
        """重新打开下拉框"""
        if self._select_widget and not self._select_widget.expanded:
            self._select_widget.action_show_overlay()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Switch 变化事件处理（布尔字段）"""
        if self._suppress_events:
            return
        if event.switch != self._switch_widget:
            return

        values = ["true"] if event.value else []
        self.post_message(self.FieldChanged(self._field.name, values))

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """RadioSet 变化事件处理（排他分组）"""
        if self._suppress_events:
            return
        if event.radio_set != self._radio_set_widget:
            return

        option_id = getattr(event.pressed, "name", None)
        values = [option_id] if option_id else []
        self.post_message(self.FieldChanged(self._field.name, values))

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Checkbox 变化事件处理（许可证列表等）"""
        if self._suppress_events:
            return

        # 仅处理本字段的 checkbox 集合
        if not self._licence_checkboxes:
            return
        # Checkbox.Changed 事件中，使用 event.checkbox 获取触发的 checkbox
        checkbox = event.checkbox if hasattr(event, 'checkbox') else event.control
        if not isinstance(checkbox, Checkbox):
            return
        if checkbox not in self._licence_checkboxes.values():
            return

        selected = [lic_id for lic_id, cb in self._licence_checkboxes.items() if cb.value]
        self.post_message(self.FieldChanged(self._field.name, selected))

    def _parse_input_value(self, value: str) -> List[Any]:
        """解析输入框的值

        根据字段类型将字符串转换为适当类型的列表。

        Args:
            value: 输入框的字符串值

        Returns:
            List[Any]: 解析后的值列表
        """
        # 空值返回空列表
        if not value.strip():
            return []

        # 分割字符串
        parts = [p.strip() for p in value.split(",") if p.strip()]

        # 根据字段类型转换
        field_type = self._field.field_type

        if field_type in (FieldType.INTEGER_ARRAY, FieldType.INTEGER_SINGLE):
            try:
                return [int(p) for p in parts]
            except ValueError:
                return parts

        if field_type == FieldType.FLOAT_ARRAY:
            try:
                return [float(p) for p in parts]
            except ValueError:
                return parts

        # 字符串类型
        return parts

    def update_values(self, values: List[str]) -> None:
        """更新可选值

        外部调用此方法来更新字段的可选值列表。

        Args:
            values: 新的可选值列表
        """
        # 更新内部状态
        self._field.set_values(values)

        # 更新下拉框选项
        if self._select_widget:
            is_quick_select = self._input_widget is not None
            new_options = (
                self._build_quick_select_options()
                if is_quick_select
                else self._build_select_options()
            )
            seq = self._begin_options_update()
            try:
                self._select_widget.set_options(new_options)

                # 组合控件（Input + Select）：
                # Select 仅用于“快速选择”，默认保持占位项（select）等待用户选择。
                if is_quick_select:
                    self._select_widget.value = self.QUICK_SELECT_PROMPT_VALUE
                    if self._input_widget:
                        self._input_widget.value = self._format_selected_for_input()
                else:
                    # 纯下拉：保持 field.selected 与 Select 当前值一致（包括 set_options 内部回退后的值）
                    current = self._select_widget.value
                    valid_values = {str(opt[1]) for opt in new_options}
                    current_str = str(current) if current not in (None, Select.BLANK) else Select.BLANK
                    if current_str in valid_values:
                        self._field.set_selected([current_str])
                    elif new_options and self._field.required:
                        fallback = str(new_options[0][1])
                        self._select_widget.value = fallback
                        self._field.set_selected([fallback])
                    else:
                        self._select_widget.value = Select.BLANK
                        self._field.clear()
            finally:
                self._end_options_update(seq)

        # 更新可选值数量显示
        self._update_count_label()

    def _update_count_label(self) -> None:
        """更新可选值数量标签"""
        try:
            count_label = self.query_one(".field-count", Label)
            if self._field.values:
                count_label.update(f"({len(self._field.values)} 可选)")
            else:
                count_label.update("")
        except Exception:
            pass

    def set_loading(self, loading: bool) -> None:
        """设置加载状态

        Args:
            loading: 是否正在加载
        """
        self._field.is_loading = loading

        if loading:
            self.add_class("loading")
            if self._input_widget:
                self._input_widget.disabled = True
            if self._select_widget:
                self._select_widget.disabled = True
            if self._switch_widget:
                self._switch_widget.disabled = True
            if self._radio_set_widget:
                self._radio_set_widget.disabled = True
            for cb in self._licence_checkboxes.values():
                cb.disabled = True
            for inp in self._extent_inputs.values():
                inp.disabled = True
        else:
            self.remove_class("loading")
            if self._input_widget:
                self._input_widget.disabled = False
            if self._select_widget:
                self._select_widget.disabled = False
            if self._switch_widget:
                self._switch_widget.disabled = False
            if self._radio_set_widget:
                self._radio_set_widget.disabled = False
            for cb in self._licence_checkboxes.values():
                cb.disabled = False
            for inp in self._extent_inputs.values():
                inp.disabled = False

    def get_selected_values(self) -> List[Any]:
        """获取当前选中的值

        Returns:
            List[Any]: 选中的值列表
        """
        if self._input_widget:
            return self._parse_input_value(self._input_widget.value)
        if self._select_widget:
            value = self._select_widget.value
            if value is None or value == Select.BLANK:
                return []
            return [value]
        if self._switch_widget:
            return ["true"] if self._switch_widget.value else []
        if self._radio_set_widget:
            pressed = self._radio_set_widget.pressed_button
            option_id = getattr(pressed, "name", None)
            return [option_id] if option_id else []
        if self._licence_checkboxes:
            return [lic_id for lic_id, cb in self._licence_checkboxes.items() if cb.value]
        if self._extent_inputs:
            return self._field.selected
        return []

    def set_selected_values(self, values: List[Any]) -> None:
        """设置选中的值

        Args:
            values: 要设置的值列表
        """
        self._suppress_events = True
        try:
            # 智能排序后再存储
            sorted_values = self._smart_sort_values(values) if values else []
            self._field.set_selected(sorted_values)

            if self._input_widget:
                self._input_widget.value = self._format_selected_for_input()
            if self._select_widget:
                if self._input_widget is not None:
                    self._select_widget.value = self.QUICK_SELECT_PROMPT_VALUE
                elif sorted_values:
                    self._select_widget.value = str(sorted_values[0])
                else:
                    self._select_widget.value = Select.BLANK
            if self._switch_widget:
                self._switch_widget.value = bool(values) and str(values[0]).strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                )
            if self._radio_set_widget:
                target = str(values[0]) if values else None
                for button in self._radio_set_widget.query(RadioButton):
                    button.value = bool(target) and getattr(button, "name", None) == target
            if self._licence_checkboxes:
                selected_ids = {str(v) for v in values}
                for lic_id, cb in self._licence_checkboxes.items():
                    cb.value = lic_id in selected_ids
            if self._extent_inputs:
                if len(values) == 4:
                    n, w, s, e = values
                    self._extent_inputs["n"].value = str(n)
                    self._extent_inputs["w"].value = str(w)
                    self._extent_inputs["s"].value = str(s)
                    self._extent_inputs["e"].value = str(e)
        finally:
            self._suppress_events = False

    def clear(self) -> None:
        """清空字段值"""
        self._suppress_events = True
        try:
            self._field.clear()
            if self._input_widget:
                self._input_widget.value = ""
            if self._select_widget:
                if self._input_widget is not None:
                    # 快速选择模式：恢复到提示选项
                    self._select_widget.value = self.QUICK_SELECT_PROMPT_VALUE
                elif not self._field.required:
                    # 非必填字段：可以清空
                    self._select_widget.clear()
                else:
                    # 必填字段：选择第一个选项，并同步内部状态
                    options = self._build_select_options()
                    if options:
                        fallback = str(options[0][1])
                        self._select_widget.value = fallback
                        self._field.set_selected([fallback])
            if self._switch_widget:
                self._switch_widget.value = False
            if self._radio_set_widget:
                for button in self._radio_set_widget.query(RadioButton):
                    button.value = False
            for cb in self._licence_checkboxes.values():
                cb.value = False
            for inp in self._extent_inputs.values():
                inp.value = ""
        finally:
            self._suppress_events = False

    @property
    def field_name(self) -> str:
        """字段名称"""
        return self._field.name

    @property
    def is_valid(self) -> bool:
        """字段值是否有效

        必填字段需要有值才有效。
        """
        if not self._field.required:
            return True
        values = self.get_selected_values()
        return len(values) > 0

    def _get_exclusive_group_options(self) -> List[Dict[str, str]]:
        """提取 ExclusiveGroupWidget 的选项列表。

        返回格式：
            [{"id": "...", "label": "..."}, ...]
        """
        # 优先使用约束/可选值列表（若已由 constraints 填充）
        if self._field.values:
            return [{"id": str(v), "label": str(v)} for v in self._field.values]

        raw_details = self._field.definition.details
        inner_details = raw_details.get("details", {})

        # 检查 children 字段（ExclusiveGroupWidget 的子组件列表）
        children = raw_details.get("children")
        if isinstance(children, list) and children:
            return [{"id": str(c), "label": str(c)} for c in children]

        # 检查 options/choices/items/values 字段
        for key in ("options", "choices", "items", "values"):
            raw = inner_details.get(key)
            if isinstance(raw, list) and raw:
                if all(isinstance(x, dict) for x in raw):
                    options: List[Dict[str, str]] = []
                    for item in raw:
                        if not isinstance(item, dict) or not item.get("id"):
                            continue
                        opt_id = str(item["id"])
                        opt_label = str(item.get("label") or opt_id)
                        options.append({"id": opt_id, "label": opt_label})
                    if options:
                        return options
                return [{"id": str(x), "label": str(x)} for x in raw if x is not None]
            if isinstance(raw, dict) and raw:
                return [{"id": str(k), "label": str(v)} for k, v in raw.items()]

        # 兜底：若只有 default，则至少提供一个可选项避免空白
        default_value = inner_details.get("default")
        if default_value is not None:
            dv = str(default_value)
            return [{"id": dv, "label": dv}]

        return []

    def _get_geo_extent_initial_values(self) -> Dict[str, str]:
        """获取地理范围输入框的初始显示值（字符串）。"""
        if len(self._field.selected) == 4:
            n, w, s, e = self._field.selected
            return {"n": str(n), "w": str(w), "s": str(s), "e": str(e)}

        details = self._field.definition.details.get("details", {})
        default_value = details.get("default")
        if isinstance(default_value, dict):
            keys = set(default_value.keys())
            if {"n", "w", "s", "e"}.issubset(keys):
                return {
                    "n": str(default_value.get("n", "")),
                    "w": str(default_value.get("w", "")),
                    "s": str(default_value.get("s", "")),
                    "e": str(default_value.get("e", "")),
                }
            if {"n", "e", "s", "w"}.issubset(keys):
                return {
                    "n": str(default_value.get("n", "")),
                    "w": str(default_value.get("w", "")),
                    "s": str(default_value.get("s", "")),
                    "e": str(default_value.get("e", "")),
                }
        if isinstance(default_value, (list, tuple)) and len(default_value) == 4:
            n, w, s, e = default_value
            return {"n": str(n), "w": str(w), "s": str(s), "e": str(e)}

        return {"n": "", "w": "", "s": "", "e": ""}

    def _parse_geo_extent_inputs(self) -> Optional[List[float]]:
        """解析 4 个地理范围输入框。

        返回：
        - 4 个值都有效：返回 [N, W, S, E]
        - 仍在编辑/存在非法值：返回 None（不触发消息）
        """
        if not self._extent_inputs:
            return None

        raw = {k: self._extent_inputs[k].value.strip() for k in ("n", "w", "s", "e")}
        if any(v == "" for v in raw.values()):
            return None

        try:
            n = float(raw["n"])
            w = float(raw["w"])
            s = float(raw["s"])
            e = float(raw["e"])
        except ValueError:
            return None

        return [n, w, s, e]


class DynamicFormFieldsContainer(Vertical):
    """动态表单字段容器

    管理多个动态字段组件的容器，提供统一的字段访问接口。
    """

    DEFAULT_CSS = """
    DynamicFormFieldsContainer {
        height: auto;
        padding: 1 0;
    }
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """初始化容器"""
        super().__init__(name=name, id=id, classes=classes)
        self._field_widgets: Dict[str, DynamicFieldWidget] = {}

    def render_fields(
        self,
        fields: Dict[str, DynamicFormField],
        on_complete: Optional[callable] = None,
    ) -> None:
        """渲染字段组件

        根据字段状态字典创建并渲染所有字段组件。

        Args:
            fields: 字段状态字典
            on_complete: 挂载完成后的回调函数（可选）
        """
        # 清除现有字段
        self._field_widgets.clear()

        # 收集需要移除的旧 widget ID
        old_widget_ids = []
        for child in list(self.children):
            if child.id:
                old_widget_ids.append(child.id)

        # 移除所有子组件
        for child in list(self.children):
            child.remove()

        # 如果没有旧组件需要移除，直接挂载新组件
        if not old_widget_ids:
            self._mount_new_fields(fields)
            if on_complete:
                on_complete()
        else:
            # 使用延迟挂载，确保旧 widget 完全从 ID 注册表中移除
            def _do_mount():
                # 再次检查是否还有旧 widget 存在（防御性编程）
                for widget_id in old_widget_ids:
                    try:
                        old_widget = self.app.query_one(f"#{widget_id}")
                        # 如果还能找到，强制移除
                        if old_widget:
                            old_widget.remove()
                    except Exception:
                        pass  # 已经被移除了，忽略

                self._mount_new_fields(fields)
                if on_complete:
                    on_complete()

            # 延迟 0.1 秒，确保旧 widget 完全从 ID 注册表中移除
            self.set_timer(0.1, _do_mount)

    def _mount_new_fields(self, fields: Dict[str, DynamicFormField]) -> None:
        """挂载新的字段组件

        Args:
            fields: 字段状态字典
        """
        # 创建新字段组件
        widgets_to_mount = []
        for field_name, field in fields.items():
            widget = DynamicFieldWidget(field, id=f"field-{field_name}")
            self._field_widgets[field_name] = widget
            widgets_to_mount.append(widget)

        # 批量挂载所有字段
        if widgets_to_mount:
            self.mount_all(widgets_to_mount)

    def get_field_widget(self, field_name: str) -> Optional[DynamicFieldWidget]:
        """获取指定字段的组件

        Args:
            field_name: 字段名称

        Returns:
            Optional[DynamicFieldWidget]: 字段组件
        """
        return self._field_widgets.get(field_name)

    def update_field_values(
        self,
        field_name: str,
        values: List[str],
    ) -> None:
        """更新指定字段的可选值

        Args:
            field_name: 字段名称
            values: 新的可选值列表
        """
        widget = self.get_field_widget(field_name)
        if widget:
            widget.update_values(values)

    def set_field_loading(
        self,
        field_name: str,
        loading: bool,
    ) -> None:
        """设置指定字段的加载状态

        Args:
            field_name: 字段名称
            loading: 是否加载中
        """
        widget = self.get_field_widget(field_name)
        if widget:
            widget.set_loading(loading)

    def get_all_values(self) -> Dict[str, List[Any]]:
        """获取所有字段的值

        Returns:
            Dict[str, List[Any]]: 字段名到值的映射
        """
        result = {}
        for field_name, widget in self._field_widgets.items():
            values = widget.get_selected_values()
            if values:
                result[field_name] = values
        return result

    def validate(self) -> List[str]:
        """验证所有字段

        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        for field_name, widget in self._field_widgets.items():
            if not widget.is_valid:
                errors.append(f"{widget._field.label} 是必填字段")
        return errors

    def clear_all(self) -> None:
        """清空所有字段"""
        for widget in self._field_widgets.values():
            widget.clear()
