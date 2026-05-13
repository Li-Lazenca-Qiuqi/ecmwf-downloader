"""
ECMWF Downloader TUI 导航侧边栏组件

提供左侧导航菜单，支持页面切换和当前页面高亮显示。
支持方向键导航（上下键切换页面，Enter键确认）。
"""

from typing import Iterable

from textual.containers import Vertical, Container
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Button, Label


class NavigationSidebar(Vertical):
    """导航侧边栏组件

    功能：
    - 显示应用标题和Logo区域
    - 显示5个导航按钮（首页/任务/下载/账号/配置）
    - 高亮当前选中页面（-active样式类 + 左侧指示条）
    - 响应点击事件，通知App切换页面
    - 支持键盘快捷键（h/t/d/a/c，通过App.action）
    - 支持方向键导航（↑↓切换页面，Enter确认）
    - 显示底部提示信息

    样式特点：
    - 固定宽度28字符
    - 左侧停靠，深色背景
    - 右侧thick边框（$accent颜色）
    - 标题区域：30%主色背景 + 底部分隔线
    - 激活按钮：40%主色背景 + 左侧thick指示条
    - 悬停效果：15%主色背景柔和高亮

    键盘操作：
    - h/t/d/a/c：快捷键切换到对应页面
    - ↑方向键：移动到上一个页面（循环）
    - ↓方向键：移动到下一个页面（循环）
    - Enter：确认选择当前页面
    """

    DEFAULT_CSS = """
    /* ═══════════════════════════════════════════════════════════════
       导航侧边栏容器 - 透明背景 + 右侧边框
       ═══════════════════════════════════════════════════════════════ */
    NavigationSidebar {
        width: 28;
        dock: left;
        background: transparent;
        border-right: thick $border;
        padding: 0;
    }

    /* 确保所有子元素Container都没有边框 */
    NavigationSidebar > Container {
        border: none;
        padding: 0;
        margin: 0;
    }

    /* ═══════════════════════════════════════════════════════════════
       导航按钮容器 - 分组按钮
       ═══════════════════════════════════════════════════════════════ */
    #nav-buttons-container {
        padding: 0 1;
        margin: 1 0;
    }

    /* ═══════════════════════════════════════════════════════════════
       导航按钮 - 基础样式
       ═══════════════════════════════════════════════════════════════ */
    NavigationSidebar Button {
        width: 1fr;
        height: 3;
        margin: 0 0 1 0;
        padding: 0 2;
        text-align: left;
        border: none;
        background: transparent;
        text-style: none;
        color: $text 80%;
    }

    /* 快捷键样式 - 第一个字符（快捷键）高亮显示 */
    NavigationSidebar Button > #button-label {
        text-style: bold;
    }

    /* 悬停效果 - 柔和高亮 */
    NavigationSidebar Button:hover {
        background: transparent;
        text-style: bold;
        color: $text;
    }

    /* 激活状态 - 高亮背景 */
    NavigationSidebar Button.-active {
        background: transparent;
        text-style: bold;
        color: $text;
        border: solid #a8a8a8;
    }

    /* 激活状态悬停 - 增强效果 */
    NavigationSidebar Button.-active:hover {
        background: transparent;
        border: solid #e6e6e6;
    }

    /* ═══════════════════════════════════════════════════════════════
       分隔线
       ═══════════════════════════════════════════════════════════════ */
    #nav-separator {
        height: 1;
        margin: 1 1;
        border-top: solid $panel 80%;
    }

    /* ═══════════════════════════════════════════════════════════════
       底部提示区域
       ═══════════════════════════════════════════════════════════════ */
    #sidebar-footer {
        height: 3;
        padding: 0 1;
        margin-top: 1;
    }

    #sidebar-footer Label {
        text-align: center;
        color: $text 50%;
        text-style: italic;
    }
    """

    # 导航项配置
    NAV_ITEMS = [
        {"id": "home", "label": "H 首页", "key": "h"},
        {"id": "tasks", "label": "T 任务管理", "key": "t"},
        {"id": "download", "label": "D 下载", "key": "d"},
        {"id": "accounts", "label": "A 账号池", "key": "a"},
        {"id": "config", "label": "C 创建任务", "key": "c"},
    ]

    # 当前页面（reactive变量，会自动触发界面更新）
    current_page = reactive("home")

    def compose(self) -> Iterable:
        """构建侧边栏UI

        结构：
        - 导航按钮容器
        - 分隔线
        - 底部提示区域
        """
        # 导航按钮容器
        with Container(id="nav-buttons-container"):
            for nav_item in self.NAV_ITEMS:
                # 使用nav-前缀作为按钮ID，便于识别
                yield Button(
                    nav_item["label"],
                    id=f"nav-{nav_item['id']}",
                    classes="" if nav_item["id"] != "home" else "-active",
                )

        # 分隔线
        yield Container(id="nav-separator")

        # 底部提示区域
        yield Label("↑↓页面 Tab↔切换焦点 q退出", id="footer-label")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        # 设置初始激活状态
        self._update_active_button()

        # 让侧边栏容器本身可以聚焦
        # 这样焦点就会在侧边栏整体和内容区域之间切换，而不是在按钮之间切换
        self.can_focus = True

        # 防止按钮单独获取焦点（通过监听焦点事件）
        # 当按钮尝试获取焦点时，将焦点转发给侧边栏容器
        for nav_item in self.NAV_ITEMS:
            try:
                button = self.query_one(f"#nav-{nav_item['id']}", Button)
                # 设置按钮不可聚焦
                button.can_focus = False
            except Exception:
                pass

    def watch_current_page(self, old_page: str, new_page: str) -> None:
        """监听current_page变化，更新按钮激活状态

        Args:
            old_page: 旧页面ID
            new_page: 新页面ID
        """
        self._update_active_button()

    def _update_active_button(self) -> None:
        """更新按钮激活状态（-active样式类）"""
        # 移除所有按钮的激活状态
        for nav_item in self.NAV_ITEMS:
            button = self.query_one(f"#nav-{nav_item['id']}", Button)
            button.remove_class("-active")

        # 为当前页面的按钮添加激活状态
        try:
            current_button = self.query_one(f"#nav-{self.current_page}", Button)
            current_button.add_class("-active")
        except Exception:
            # 如果查询失败（页面ID无效），忽略错误
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件处理

        Args:
            event: 按钮按下事件
        """
        button_id = event.button.id

        # 从按钮ID中提取页面ID（移除nav-前缀）
        if button_id and button_id.startswith("nav-"):
            page_id = button_id.replace("nav-", "")

            # 更新当前页面（会触发watch_current_page）
            self.current_page = page_id

            # 通知App切换页面
            # 注意：App需要实现action_switch_page方法
            if hasattr(self.app, "action_switch_page"):
                self.app.action_switch_page(page_id)
            else:
                # 如果App还没有实现switch_page，记录警告
                self.log.warning(
                    f"App.action_switch_page() 方法未实现，无法切换到页面: {page_id}"
                )

    def on_key(self, event: Key) -> None:
        """处理键盘事件，支持方向键导航和焦点切换

        支持的按键：
        - 上箭头（up）：移动到上一个页面
        - 下箭头（down）：移动到下一个页面
        - Tab：切换焦点到右侧内容区域

        注意：Enter键不需要处理，方向键移动时页面已经跟着切换了

        Args:
            event: 键盘事件
        """
        # 获取当前页面在导航列表中的索引
        current_index = -1
        for i, nav_item in enumerate(self.NAV_ITEMS):
            if nav_item["id"] == self.current_page:
                current_index = i
                break

        # 根据按键处理
        if event.key == "up":
            # 上箭头：移动到上一个页面（循环）
            if current_index > 0:
                new_index = current_index - 1
            else:
                new_index = len(self.NAV_ITEMS) - 1  # 循环到最后一个
            self._navigate_to_index(new_index)
            event.stop()  # 阻止事件继续传播

        elif event.key == "down":
            # 下箭头：移动到下一个页面（循环）
            if current_index < len(self.NAV_ITEMS) - 1:
                new_index = current_index + 1
            else:
                new_index = 0  # 循环到第一个
            self._navigate_to_index(new_index)
            event.stop()  # 阻止事件继续传播

        elif event.key == "tab":
            # Tab键：切换焦点到右侧内容区域
            # 阻止默认的Tab行为（在按钮间切换）
            event.stop()
            # 手动将焦点设置到内容区域
            self._switch_focus_to_content()

    def _navigate_to_index(self, index: int) -> None:
        """导航到指定索引的页面

        Args:
            index: 页面索引
        """
        if 0 <= index < len(self.NAV_ITEMS):
            page_id = self.NAV_ITEMS[index]["id"]
            # 更新当前页面（会触发watch_current_page和页面切换）
            self.current_page = page_id
            # 通知App切换页面
            if hasattr(self.app, "action_switch_page"):
                self.app.action_switch_page(page_id)

    def _switch_focus_to_content(self) -> None:
        """切换焦点到右侧内容区域"""
        try:
            # 获取ContentArea
            from src.ui.widgets.content_area import ContentArea
            content_area = self.app.query_one("#main-content", ContentArea)

            # 获取当前显示的内容Widget
            current_widget = content_area.get_current_content()

            if current_widget:
                # 尝试聚焦到内容Widget的第一个可聚焦子元素
                # 先尝试找Input、DataTable等可聚焦的组件
                focusable = current_widget.query_one(
                    "Input, DataTable, Button, TextArea", expect_type=None
                )

                if focusable:
                    focusable.focus()
                    self.log.info(f"焦点已切换到: {focusable.__class__.__name__}")
                else:
                    # 如果没有找到，就聚焦到内容Widget本身
                    current_widget.focus()
                    self.log.info("焦点已切换到内容区域")
            else:
                self.log.warning("没有可聚焦的内容区域")
        except Exception as e:
            self.log.warning(f"切换焦点到内容区域失败: {e}")
