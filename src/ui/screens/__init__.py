"""
TUI 屏幕模块

包含所有屏幕类的定义。
"""

from src.ui.screens.base_screen import BaseScreen
from src.ui.screens.home_screen import HomeScreen
from src.ui.screens.tasks_screen import TasksScreen
from src.ui.screens.download_screen import DownloadScreen
from src.ui.screens.accounts_screen import AccountsScreen

__all__ = ["BaseScreen", "HomeScreen", "TasksScreen", "DownloadScreen", "AccountsScreen"]
