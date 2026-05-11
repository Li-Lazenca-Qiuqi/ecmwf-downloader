"""
UI测试专用fixtures配置

提供屏幕和组件测试所需的共享fixtures。
"""

import pytest
from unittest.mock import Mock
from pathlib import Path
from src.ui.app import ECMWFDownloaderApp


# 配置pytest-asyncio自动模式
# 这使得所有async def测试函数自动被视为异步测试
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def temp_config_dir(tmp_path):
    """创建临时配置目录

    Returns:
        tuple: (config_dir, data_dir) 临时目录路径
    """
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_dir.mkdir()
    data_dir.mkdir()
    return config_dir, data_dir


@pytest.fixture
def mock_app(temp_config_dir):
    """创建Mock应用实例（用于屏幕测试）

    提供一个轻量级的mock应用，用于测试屏幕组件，
    避免初始化完整的应用实例。

    Returns:
        Mock: 模拟的应用对象，包含progress_manager和account_pool
    """
    config_dir, data_dir = temp_config_dir

    app = Mock(spec=ECMWFDownloaderApp)
    app.progress_manager = Mock()
    app.account_pool = Mock()
    app.call_from_thread = Mock()
    app.notify = Mock()
    app.log = Mock()

    # 设置默认返回值 - 概要统计
    app.progress_manager.get_summary.return_value = {
        "total_tasks": 10,
        "downloading": 2,
        "completed": 7,
        "failed": 1,
        "overall_progress": 70.0
    }

    # 设置默认返回值 - 任务列表
    app.progress_manager.get_all_tasks.return_value = []
    app.progress_manager.get_task.return_value = None

    # 设置默认返回值 - 账号列表
    app.account_pool.get_all_accounts.return_value = []

    return app


@pytest.fixture
def app_instance(temp_config_dir):
    """创建真实应用实例（用于集成测试）

    创建一个完整的应用实例，包含真实的配置文件和数据目录。
    适用于端到端测试和导航测试。

    Returns:
        ECMWFDownloaderApp: 真实的应用实例
    """
    config_dir, data_dir = temp_config_dir
    config_file = config_dir / "default_config.yaml"
    accounts_file = config_dir / "accounts.yaml"

    # 创建最小配置文件
    config_file.write_text("""
download:
  variables: []
account_pool:
  accounts: []
""")

    # 创建空的账号配置文件
    accounts_file.write_text("""
accounts: []
""")

    app = ECMWFDownloaderApp(
        config_path=config_file,
        accounts_path=accounts_file,
        data_dir=data_dir,
    )

    return app
