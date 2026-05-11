"""
ECMWF Downloader TUI 内容区域组件

提供主内容显示区域，支持动态切换内容Widget。
支持Tab键将焦点返回到侧边栏。
"""

from typing import Iterable, Optional

import asyncio
from contextlib import suppress
from functools import partial

from textual.containers import Container, Vertical
from textual.events import Key
from textual.widget import Widget
from textual.widgets import Header
from textual.worker import Worker


class ContentArea(Vertical):
    """内容区域组件

    功能：
    - 动态加载和显示页面内容Widget
    - 保持Header和Footer固定
    - 支持页面切换

    样式：
    - 占据剩余空间
    - 垂直布局
    - 主内容区域可滚动
    """

    DEFAULT_CSS = """
    ContentArea {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
    }

    #content-container {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
    }
    """

    def __init__(self, **kwargs):
        """初始化内容区域

        Args:
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._current_content_widget: Optional[Widget] = None
        self._switch_serial = 0
        self._switch_worker: Optional[Worker] = None

    async def shutdown(self) -> None:
        """退出前清理 ContentArea 内部异步任务与内容。

        说明：ContentArea 使用 asyncio.create_task 执行页面 mount/remove。
        若退出时仍有 pending task，可能触发“Task was destroyed but it is pending”
        或导致事件循环/终端状态清理异常。
        """
        # 取消正在进行的内容切换 worker（使用 Textual WorkerManager，确保退出可清理）
        if self._switch_worker is not None and self._switch_worker.is_running:
            self._switch_worker.cancel()
            with suppress(asyncio.CancelledError):
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._switch_worker.wait(), timeout=1.0)
        self._switch_worker = None

        # 退出阶段交给 Textual 完成 DOM 的最终卸载；这里只清理本组件内部状态，
        # 避免 remove_children 在退出时触发额外的 DOM 操作而导致卡住。
        self._current_content_widget = None
        self._switch_serial += 1

    def compose(self) -> Iterable:
        """构建内容区域UI"""
        yield Header()
        with Container(id="content-container"):
            # 主内容容器，初始为空
            pass

    def switch_content(self, content_widget: Widget) -> None:
        """切换内容区域显示的 Widget（同步入口）

        说明：Textual 7+ 的 mount/remove 是异步的，这里使用 Textual 的 Worker
        系统托管切换逻辑，避免自行 create_task 导致退出清理困难。
        """
        self._current_content_widget = content_widget
        self._switch_serial += 1
        serial = self._switch_serial

        def _schedule() -> None:
            # 取消旧的切换 worker
            if self._switch_worker is not None and self._switch_worker.is_running:
                self._switch_worker.cancel()
            # exclusive=True 确保同组只跑一个（减少并发 DOM 操作）
            self._switch_worker = self.run_worker(
                partial(self._apply_content, serial),
                name="content-switch",
                group="content-switch",
                exclusive=True,
                exit_on_error=False,
            )

        self.call_after_refresh(_schedule)

    def clear_content(self) -> None:
        """清空内容区域（同步入口）"""
        if self._current_content_widget is None:
            return

        self._current_content_widget = None
        self._switch_serial += 1
        serial = self._switch_serial

        def _schedule() -> None:
            if self._switch_worker is not None and self._switch_worker.is_running:
                self._switch_worker.cancel()
            self._switch_worker = self.run_worker(
                partial(self._apply_content, serial),
                name="content-clear",
                group="content-switch",
                exclusive=True,
                exit_on_error=False,
            )

        self.call_after_refresh(_schedule)

    async def _apply_content(self, serial: int) -> None:
        """根据当前状态应用内容（Textual 7+ 需要 await mount/remove）"""
        if serial != self._switch_serial:
            return

        try:
            content_container = self.query_one("#content-container", Container)
        except Exception:
            return

        try:
            await content_container.remove_children()

            if serial != self._switch_serial:
                return

            if self._current_content_widget is not None:
                await content_container.mount(self._current_content_widget)
                self.log.info(
                    f"内容区域已切换到: {self._current_content_widget.__class__.__name__}"
                )
            else:
                self.log.info("内容区域已清空")
        except asyncio.CancelledError:
            # 切换被取消（例如快速切页/退出），不记录为异常
            return
        except Exception as e:
            self.log.warning(f"应用内容区域变更失败: {e}")
            return

        # 将焦点设置回侧边栏（NavigationSidebar）
        try:
            sidebar = self.app.query_one("NavigationSidebar")
            sidebar.focus()
            self.log.debug("焦点已返回到侧边栏")
        except Exception as e:
            self.log.warning(f"设置焦点到侧边栏失败: {e}")

    def get_current_content(self) -> Optional[Widget]:
        """获取当前显示的内容Widget

        Returns:
            Optional[Widget]: 当前内容Widget，如果没有则返回None
        """
        return self._current_content_widget

    def on_key(self, event: Key) -> None:
        """处理键盘事件，支持Tab键返回侧边栏

        当焦点在内容区域时，按Tab键将焦点返回到侧边栏，
        而不是在内容区域的控件间切换。

        Args:
            event: 键盘事件
        """
        # Tab键：返回焦点到侧边栏
        if event.key == "tab":
            event.stop()  # 阻止默认的Tab行为（在控件间切换）
            self._return_focus_to_sidebar()

    def _return_focus_to_sidebar(self) -> None:
        """将焦点返回到侧边栏"""
        try:
            from src.ui.widgets.navigation_sidebar import NavigationSidebar
            sidebar = self.app.query_one(NavigationSidebar)
            sidebar.focus()
            self.log.info("焦点已返回到侧边栏")
        except Exception as e:
            self.log.warning(f"返回焦点到侧边栏失败: {e}")
