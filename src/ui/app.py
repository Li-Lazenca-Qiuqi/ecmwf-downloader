"""
ECMWF Downloader TUI 应用主入口

基于 Textual 框架的终端用户界面应用。
采用侧边栏布局架构，包含导航侧边栏和内容区域。
"""

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Dict, Iterable, Optional, TYPE_CHECKING

from textual import work
from textual.app import App
from textual.containers import Horizontal

from src.ui.widgets.content_area import ContentArea
from src.ui.widgets.contents.accounts_content import AccountsContent
from src.ui.pages.create_task import CreateTaskView
from src.ui.widgets.contents.download_content import DownloadContent
from src.ui.widgets.contents.home_content import HomeContent
from src.ui.widgets.contents.tasks_content import TasksContent
from src.ui.widgets.navigation_sidebar import NavigationSidebar
from src.utils.config_initializer import initialize_config

if TYPE_CHECKING:
    from src.core.account_pool import AccountPool
    from src.core.progress import ProgressManager
    from src.core.queue_scheduler import DownloadQueueScheduler
    from src.ui.widgets.contents.home_content import HomeContent
    from src.ui.widgets.contents.tasks_content import TasksContent
    from src.ui.widgets.contents.download_content import DownloadContent
    from src.ui.widgets.contents.accounts_content import AccountsContent
    from src.ui.pages.create_task import CreateTaskView


class ECMWFDownloaderApp(App):
    """ECMWF下载器TUI应用主类

    提供基于Textual框架的终端用户界面，采用侧边栏布局架构。

    布局结构：
    - 左侧：NavigationSidebar（导航菜单）
    - 右侧：ContentArea（内容区域）
    - 底部：Footer（状态栏）

    采用延迟加载模式初始化核心模块，提高启动性能。
    """

    # 应用标题
    TITLE = "ECMWF Downloader"

    # 全局 CSS 样式
    CSS = """
    /* =============================================================
       主题变量 - 终端原生灰度主题

       保持背景透明，尽量使用终端自身底色，只保留必要的灰度层级。
       ============================================================= */
    $bg: ansi_default;
    $panel: #666666;
    $panel-lighten-1: #888888;
    $surface: ansi_default;
    $border: #777777;

    $text: ansi_default;
    $text-muted: #a8a8a8;

    $primary: #d0d0d0;
    $accent: #d0d0d0;
    $success: #d0d0d0;
    $warning: #b8b8b8;
    $error: #d0d0d0;

    /* =============================================================
       基础布局
       ============================================================= */
    App {
        background: $bg;
        color: $text;
    }

    Screen {
        background: $bg;
        color: $text;
    }

    #app-body {
        height: 1fr;
    }

    NavigationSidebar {
        height: 1fr;
    }

    ContentArea {
        height: 1fr;
    }

    #content-container {
        background: transparent;
    }

    /* =============================================================
       Header / Footer
       ============================================================= */
    Header {
        background: transparent;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 0 2;
    }

    Footer {
        background: transparent;
        color: $text-muted;
        padding: 0 1;
    }

    /* =============================================================
       容器与通用文本
       ============================================================= */
    .content-container {
        width: 1fr;
        height: 1fr;
        padding: 1 1;
    }

    .page-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 2;
    }

    .table-section {
        width: 1fr;
        height: 1fr;
    }

    /* =============================================================
       按钮（圆角、紧凑、美观）
       ============================================================= */
    Button {
        height: 3;
        min-width: 8;
        padding: 0 2;
        margin: 0 1;
        background: transparent;
        color: $text;
        border: wide $border;
        text-style: none;
        text-align: center;
    }

    Button:hover {
        background: transparent;
        border: wide #a8a8a8;
        text-style: bold;
    }

    Button:focus {
        background: transparent;
        border: wide #e6e6e6;
        text-style: bold;
    }

    Button:disabled {
        background: transparent;
        border: wide $border 50%;
        color: $text 50%;
        opacity: 0.6;
    }

    /* 按钮变体样式 */
    Button.-primary {
        background: transparent;
        border: wide #e6e6e6;
        text-style: bold;
    }

    Button.-primary:hover {
        background: transparent;
        border: wide #e6e6e6;
    }

    /* =============================================================
       输入框
       ============================================================= */
    Input {
        height: 3;
        padding: 0 1;
        border: wide $panel;
        background: transparent;
        color: $text;
    }

    Input:focus {
        border: wide $accent;
    }

    Input > .input--placeholder {
        color: $text-muted;
    }

    Input.-invalid {
        border: wide $error;
    }

    /* =============================================================
       表格（DataTable / TaskTable / AccountTable）
       ============================================================= */
    DataTable {
        border: thick $border;
        background: transparent;
        color: $text;
    }

    DataTable > .datatable--header {
        background: transparent;
        color: $text;
        text-style: bold;
        border-bottom: thick $border;
        padding: 0 1;
    }

    DataTable > .datatable--header:hover {
        background: transparent;
    }

    DataTable > .datatable--cursor {
        background: transparent;
        color: $text;
        text-style: bold;
        border-left: thick #e6e6e6;
    }

    DataTable > .datatable--hover {
        background: transparent;
        text-style: bold;
    }

    DataTable > .datatable--even-row {
        background: transparent;
    }

    DataTable > .datatable--odd-row {
        background: transparent;
    }

    /* =============================================================
       HomeContent 首页样式
       ============================================================= */
    HomeContent {
        width: 1fr;
        height: 1fr;
    }

    HomeContent #home-container {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        padding: 1 1;
    }

    HomeContent #app-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }

    HomeContent #app-subtitle {
        text-align: center;
        text-style: italic;
        margin-top: 0;
        margin-bottom: 2;
        color: $text 60%;
    }

    HomeContent #stats-section {
        width: 1fr;
        height: auto;
        margin: 1 0;
    }

    HomeContent .stat-card {
        width: 1fr;
        height: auto;
        border: solid $border;
        padding: 1;
        margin: 0;
        background: transparent;
    }

    HomeContent .stat-card:last-child {
        margin-left: 1;
    }

    HomeContent .card-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    HomeContent .stat-item {
        text-align: left;
        text-style: none;
        color: $text 90%;
        margin: 0;
    }

    HomeContent #recent-title {
        text-align: left;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
        margin-left: 0;
        color: $accent;
    }

    HomeContent #recent-table {
        width: 1fr;
        height: 1fr;
        min-height: 10;
        margin: 1 0 3 0;
    }

    /* =============================================================
       TasksContent 任务列表样式
       ============================================================= */
    TasksContent {
        width: 1fr;
        height: 1fr;
    }

    TasksContent #tasks-container {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        padding: 1 1;
    }

    TasksContent #tasks-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    TasksContent #filter-container {
        width: 1fr;
        height: auto;
        margin: 1 0;
        padding: 0;
    }

    TasksContent #filter-container Button {
        width: 1fr;
        margin: 0;
    }

    TasksContent #filter-container #filter-pending,
    TasksContent #filter-container #filter-downloading,
    TasksContent #filter-container #filter-completed,
    TasksContent #filter-container #filter-failed {
        margin-left: 1;
    }

    TasksContent #tasks-table {
        width: 1fr;
        height: 1fr;
        margin: 1 0;
    }

    TasksContent #actions-container {
        width: 1fr;
        height: auto;
        margin: 1 0;
        padding: 0;
    }

    TasksContent #actions-container Button {
        width: 1fr;
        margin: 0;
    }

    TasksContent #actions-container Button.-middle,
    TasksContent #actions-container Button.-last {
        margin-left: 1;
    }

    /* =============================================================
       DownloadContent 下载管理样式
       ============================================================= */
    DownloadContent {
        width: 1fr;
        height: 1fr;
    }

    DownloadContent #download-container {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        padding: 1 1;
    }

    DownloadContent #download-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    DownloadContent #progress-card {
        width: 1fr;
        height: auto;
        border: solid $border;
        padding: 1 0;
        margin: 1 0;
        background: transparent;
    }

    DownloadContent #progress-row {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    DownloadContent #progress-label {
        width: auto;
        text-style: bold;
        color: $accent;
        margin-right: 1;
    }

    DownloadContent #overall-progress {
        width: 1fr;
        margin: 0;
    }

    DownloadContent #stats-row {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    DownloadContent .stat-item {
        width: 1fr;
        text-align: center;
        margin: 0;
    }

    DownloadContent .stat-value {
        color: $accent;
        text-style: bold;
    }

    DownloadContent #active-tasks-section {
        width: 1fr;
        height: 1fr;
        margin: 1 0;
    }

    DownloadContent #active-label {
        text-align: left;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }

    DownloadContent #active-table {
        width: 1fr;
        height: 1fr;
        margin: 1 0 0 0;
    }

    DownloadContent #control-section {
        width: 1fr;
        height: auto;
        margin: 1 0 0 0;
        padding: 0;
    }

    DownloadContent #control-section Button {
        width: 1fr;
        margin: 0;
    }

    DownloadContent #control-section Button.-middle,
    DownloadContent #control-section Button.-last {
        margin-left: 1;
    }

    /* =============================================================
       AccountsContent 账号管理样式
       ============================================================= */
    AccountsContent {
        width: 1fr;
        height: 1fr;
    }

    AccountsContent #accounts-container {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        padding: 1 1;
        margin: 0;
    }

    AccountsContent #accounts-title {
        text-align: left;
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 2;
        margin-left: 0;
    }

    AccountsContent #table-section {
        width: 1fr;
        height: 1fr;
        margin: 0;
        padding: 0;
    }

    AccountsContent #accounts-table {
        width: 1fr;
        height: 1fr;
        border: solid $border;
        margin: 1 0;
    }

    AccountsContent #actions-section {
        width: 1fr;
        height: auto;
        margin: 1 0;
        padding: 0;
    }

    AccountsContent #actions-section Button {
        width: 1fr;
        margin: 0;
        padding: 0 1;
    }

    AccountsContent #actions-section #btn-edit,
    AccountsContent #actions-section #btn-delete,
    AccountsContent #actions-section #btn-enable,
    AccountsContent #actions-section #btn-disable,
    AccountsContent #actions-section #btn-refresh {
        margin-left: 1;
    }

    /* =============================================================
       通知样式
       ============================================================= */
    Notification {
        background: transparent;
        border: tall $border;
        padding: 1 2;
    }

    /* =============================================================
       状态颜色样式
       ============================================================= */
    .status-pending {
        color: $text 50%;
        text-style: italic;
    }

    .status-downloading {
        color: $primary;
        text-style: bold;
    }

    .status-completed {
        color: $success;
        text-style: bold;
    }

    .status-failed {
        color: $error;
        text-style: bold;
    }

    .status-cancelled {
        color: $warning;
        text-style: bold;
    }

    .status-retrying {
        color: $accent;
        text-style: bold;
    }
    """

    # 全局快捷键绑定
    # Textual的BINDINGS要求action必须是方法名，不能带参数
    # 因此为每个页面创建专门的action方法
    BINDINGS = [
        ("q", "quit", "退出"),
        ("ctrl+c", "quit", "退出"),
        ("h", "go_home", "首页"),
        ("t", "go_tasks", "任务"),
        ("d", "go_download", "下载"),
        ("a", "go_accounts", "账号池"),
        ("c", "go_config", "创建任务"),
    ]

    def __init__(
        self,
        config_path: Optional[Path] = None,
        accounts_path: Optional[Path] = None,
        data_dir: Optional[Path] = None,
    ):
        """初始化应用

        Args:
            config_path: 配置文件路径（可选，默认使用 config/default_config.yaml）
            accounts_path: 账号配置文件路径（可选，默认使用 config/accounts.yaml）
            data_dir: 数据目录路径（可选，默认使用 data/）
        """
        super().__init__()

        # 配置文件路径
        self._config_path = config_path or Path("config/default_config.yaml")
        self._accounts_path = accounts_path or Path("config/accounts.yaml")
        self._data_dir = data_dir or Path("data")

        # 核心模块实例（延迟加载）
        self._account_pool: Optional["AccountPool"] = None
        self._progress_manager: Optional["ProgressManager"] = None
        self._queue_scheduler: Optional["DownloadQueueScheduler"] = None

        # 确保数据目录存在
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        if not self._data_dir.exists():
            self._data_dir.mkdir(parents=True, exist_ok=True)

    def compose(self) -> Iterable:
        """构建应用UI

        采用侧边栏布局：
        - 左侧：NavigationSidebar（导航菜单）
        - 右侧：ContentArea（内容区域，已包含Header和Footer）
        """
        with Horizontal(id="app-body"):
            yield NavigationSidebar()
            yield ContentArea(id="main-content")

    def on_mount(self) -> None:
        """应用挂载时的生命周期钩子

        在应用启动后、显示第一个屏幕前调用。
        用于初始化应用状态、加载数据等。
        """
        # 初始化配置文件（如果不存在则从 example 复制）
        initialize_config()

        self.log.info("ECMWF Downloader TUI 启动")
        self.log.info(f"配置文件: {self._config_path}")
        self.log.info(f"账号配置: {self._accounts_path}")
        self.log.info(f"数据目录: {self._data_dir}")

        # 显示首页（每次切换都会创建新的 Widget 实例）
        self.action_switch_page("home")

        # 设置初始焦点在侧边栏
        try:
            sidebar = self.query_one(NavigationSidebar)
            sidebar.focus()
            self.log.info("初始焦点已设置到侧边栏")
        except Exception as e:
            self.log.warning(f"设置初始焦点失败: {e}")

        # 显示欢迎消息
        self.notify(
            "欢迎使用 ECMWF Downloader！按 Tab 键在侧边栏和内容区域间切换，按 'q' 或 Ctrl+C 退出",
            title="欢迎",
            severity="information",
            timeout=5,
        )

        # 初始化队列调度器（延迟加载，首次访问时自动启动）
        # 这里显式调用以确保在启动时就初始化
        _ = self.queue_scheduler

    def action_switch_page(self, page_id: str) -> None:
        """切换当前显示的页面（同步入口）

        兼容测试与同步调用方；实际的 mount/remove 在 ContentArea 内部异步执行。

        注意：每次切换都创建新的 Widget 实例，避免 Textual 中复用已卸载组件的问题。
        """
        # 页面 Widget 类映射
        page_classes = {
            "home": HomeContent,
            "tasks": TasksContent,
            "download": DownloadContent,
            "accounts": AccountsContent,
            "config": CreateTaskView,
        }

        # 验证page_id
        if page_id not in page_classes:
            self.log.error(f"无效的页面ID: {page_id}")
            return

        # 更新侧边栏的激活状态
        try:
            sidebar = self.query_one(NavigationSidebar)
            sidebar.current_page = page_id
        except Exception as e:
            self.log.warning(f"更新侧边栏状态失败: {e}")

        # 切换内容区域 - 每次创建新实例
        try:
            content_area = self.query_one("#main-content", ContentArea)
            # 每次创建新的 Widget 实例，避免复用已卸载组件的问题
            content_widget = page_classes[page_id](app=self)
            content_area.switch_content(content_widget)
            self.log.info(f"页面已切换到: {page_id}")
        except Exception as e:
            self.log.error(f"切换页面失败: {e}")

    # 专门的action方法供快捷键调用（Textual要求BINDINGS中的action必须是方法名）
    def action_go_home(self) -> None:
        """快捷键h：切换到首页"""
        self.action_switch_page("home")

    def action_go_tasks(self) -> None:
        """快捷键t：切换到任务页"""
        self.action_switch_page("tasks")

    def action_go_download(self) -> None:
        """快捷键d：切换到下载页"""
        self.action_switch_page("download")

    def action_go_accounts(self) -> None:
        """快捷键a：切换到账号页"""
        self.action_switch_page("accounts")

    def action_go_config(self) -> None:
        """快捷键c：切换到配置页"""
        self.action_switch_page("config")

    @property
    def account_pool(self) -> "AccountPool":
        """获取账号池实例（延迟加载）

        Returns:
            AccountPool: 账号池管理器实例

        Raises:
            Exception: 账号配置文件加载失败
        """
        if self._account_pool is None:
            from src.core.account_pool import AccountPool

            self._account_pool = AccountPool(
                config_file=self._accounts_path,
                auto_disable_threshold=5,
            )
            self.log.info("账号池初始化完成")
        return self._account_pool

    @property
    def progress_manager(self) -> "ProgressManager":
        """获取进度管理器实例（延迟加载）

        Returns:
            ProgressManager: 进度管理器实例
        """
        if self._progress_manager is None:
            from src.core.progress import ProgressManager

            self._progress_manager = ProgressManager(
                data_dir=self._data_dir
            )
            self.log.info("进度管理器初始化完成")
        return self._progress_manager

    @property
    def queue_scheduler(self) -> "DownloadQueueScheduler":
        """获取队列调度器实例（延迟加载）

        调度器会自动启动，定期检测 QUEUED 任务并启动下载。

        Returns:
            DownloadQueueScheduler: 队列调度器实例
        """
        if self._queue_scheduler is None:
            from src.core.queue_scheduler import DownloadQueueScheduler

            # 创建调度器（回调使用 call_from_thread 切回主线程）
            self._queue_scheduler = DownloadQueueScheduler(
                progress_manager=self.progress_manager,
                account_pool=self.account_pool,
                start_download_callback=self._start_download_from_scheduler,
                max_workers=3,
                poll_interval=1.0,
            )
            # 启动调度器
            self._queue_scheduler.start()
            self.log.info("队列调度器已启动")
        return self._queue_scheduler

    def _start_download_from_scheduler(self, task_id: str, account) -> None:
        """调度器回调：在主线程中启动下载任务

        调度器在后台线程中运行，需要通过 call_from_thread
        切回主线程来调用 @work 装饰的方法。

        Args:
            task_id: 任务ID
            account: 已分配的账号
        """
        # 使用 call_from_thread 确保在主线程中执行
        self.call_from_thread(
            self._run_download_worker,
            task_id,
            account,
        )

    @work(exclusive=False, thread=True)
    def _run_download_worker(self, task_id: str, account) -> None:
        """执行下载任务（@work 装饰，在后台线程运行）

        这是真正的下载执行入口，满足 Textual 的 @work 要求
        （self 必须是 DOMNode 子类）。

        Args:
            task_id: 任务ID
            account: 已分配的账号
        """
        from src.ui.workers.download_worker import execute_download_with_account
        execute_download_with_account(
            app=self,
            task_id=task_id,
            account=account,
            on_complete=self._on_download_complete,
        )

    def _on_download_complete(self, task_id: str) -> None:
        """下载完成回调

        通知调度器任务已完成，释放活动槽位。

        Args:
            task_id: 完成的任务ID
        """
        if self._queue_scheduler is not None:
            self._queue_scheduler.on_task_completed(task_id)

    def on_unmount(self) -> None:
        """应用卸载时的生命周期钩子

        在应用退出前调用。
        用于保存状态、清理资源等。
        """
        self.log.info("ECMWF Downloader TUI 退出")

        # 保存进度
        if self._progress_manager is not None:
            try:
                self._progress_manager.save()
                self.log.info("进度已保存")
            except Exception as e:
                # 退出阶段不可抛异常，否则可能导致终端状态无法恢复
                self.log.error(f"保存进度失败（已忽略）: {e}")

    async def action_quit(self) -> None:
        """退出应用（带清理）

        处理：
        - 取消 ContentArea 内部异步切换任务（避免退出时遗留 pending task）
        - 取消并等待 Textual workers（避免后台线程/任务阻塞退出）
        - 尝试保存进度（失败不影响退出）
        """
        # 先做最佳努力清理，避免异常中断退出流程
        try:
            await self._cleanup_before_exit()
        except Exception as e:
            self.log.error(f"退出清理异常（已忽略）: {e}")

        self.exit()

    async def _cleanup_before_exit(self) -> None:
        """退出前清理资源（不抛异常）"""
        # 1) 停止队列调度器
        if self._queue_scheduler is not None:
            try:
                self._queue_scheduler.stop()
                self.log.info("队列调度器已停止")
            except Exception as e:
                self.log.warning(f"停止队列调度器失败（已忽略）: {e}")

        # 2) 停止内容区域的异步切换任务
        try:
            content_area = self.query_one("#main-content", ContentArea)
            await content_area.shutdown()
        except Exception as e:
            self.log.warning(f"清理内容区域失败（已忽略）: {e}")

        # 3) 取消并等待 Textual workers（含 @work(thread=True)）
        try:
            self.workers.cancel_all()
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self.workers.wait_for_complete(), timeout=1.0
                )
        except Exception as e:
            self.log.warning(f"清理后台任务失败（已忽略）: {e}")

        # 4) 保存进度（失败不影响退出）
        if self._progress_manager is not None:
            try:
                self._progress_manager.save()
            except Exception as e:
                self.log.error(f"退出前保存进度失败（已忽略）: {e}")


# 创建应用的便捷函数（供 __main__.py 使用）
def create_app(
    config_path: Optional[Path] = None,
    accounts_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> ECMWFDownloaderApp:
    """创建应用实例的便捷函数

    Args:
        config_path: 配置文件路径
        accounts_path: 账号配置文件路径
        data_dir: 数据目录路径

    Returns:
        ECMWFDownloaderApp: 应用实例
    """
    return ECMWFDownloaderApp(
        config_path=config_path,
        accounts_path=accounts_path,
        data_dir=data_dir,
    )
