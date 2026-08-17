"""
ECMWF下载器账号池管理模块

实现多API账号的轮换使用、状态管理和线程安全访问。
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from src.core.config import AccountInfo, AccountPoolConfig, AccountStatus
from src.core.exceptions import AccountPoolError


class AccountPool:
    """账号池管理器

    管理多个ECMWF API账号，支持轮换策略、自动禁用失效账号、使用统计等功能。
    所有操作都是线程安全的，可在多线程环境下并行获取账号。
    """

    def __init__(self, config_file: Optional[Path] = None, auto_disable_threshold: int = 5):
        """初始化账号池

        Args:
            config_file: 账号配置文件路径（YAML格式）
            auto_disable_threshold: 连续失败多少次后自动禁用账号

        Raises:
            AccountPoolError: 配置文件加载失败或没有可用账号
        """
        self.config_file = config_file
        self.auto_disable_threshold = auto_disable_threshold

        # 账号列表
        self.accounts: List[AccountInfo] = []

        # 轮换索引（用于并行获取不同账号）
        self._current_index = 0

        # 线程安全锁
        self._lock = threading.RLock()

        # 如果提供了配置文件，则加载
        if config_file is not None:
            self.load_from_file(config_file)

        # 旧核心 API 保持“无账号即配置错误”的契约；新 CLI/Web 使用
        # ecmwf_downloader.application.AccountService，可从空池开始添加账号。
        if not self.accounts:
            raise AccountPoolError("账号池为空", available_count=0)

    def load_from_file(self, config_file: Path) -> None:
        """从YAML文件加载账号配置

        Args:
            config_file: 配置文件路径

        Raises:
            AccountPoolError: 文件读取失败或格式错误
        """
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "accounts" not in data:
                raise AccountPoolError(f"配置文件格式错误: {config_file}")

            # 解析账号列表（处理 None 情况）
            accounts_data = data["accounts"] or []
            self.accounts = [AccountInfo(**acc) for acc in accounts_data]

            # 重置索引
            self._current_index = 0

        except FileNotFoundError:
            raise AccountPoolError(
                f"账号配置文件不存在: {config_file}",
                file_path=str(config_file),
            )
        except yaml.YAMLError as e:
            raise AccountPoolError(
                f"配置文件YAML格式错误: {e}",
                file_path=str(config_file),
                original_error=e,
            )
        except Exception as e:
            raise AccountPoolError(
                f"加载账号配置失败: {e}",
                file_path=str(config_file),
                original_error=e,
            )

    def save_to_file(self, config_file: Optional[Path] = None) -> None:
        """保存账号配置到YAML文件

        Args:
            config_file: 配置文件路径，如果为None则使用初始化时的路径

        Raises:
            AccountPoolError: 文件保存失败
        """
        target_file = config_file or self.config_file
        if target_file is None:
            raise AccountPoolError("未指定配置文件路径")

        try:
            with self._lock:
                # 转换为字典格式（使用 mode='json' 确保枚举值被正确序列化为字符串）
                data = {
                    "accounts": [acc.model_dump(mode='json') for acc in self.accounts],
                    "auto_disable_threshold": self.auto_disable_threshold,
                }

                # 写入文件（使用 safe_dump 避免生成 Python 特定标签）
                with open(target_file, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

        except Exception as e:
            raise AccountPoolError(
                f"保存账号配置失败: {e}",
                file_path=str(target_file),
                original_error=e,
            )

    def get_next_account(self) -> AccountInfo:
        """获取下一个可用账号（轮换策略，支持并行）

        使用轮换索引策略，每次调用返回不同的账号，支持多线程并行获取。
        会自动跳过已禁用和失败的账号。

        Returns:
            AccountInfo: 可用的账号信息

        Raises:
            AccountPoolError: 没有可用账号
        """
        with self._lock:
            # 筛选可用账号
            available_accounts = [
                acc
                for acc in self.accounts
                if acc.status == AccountStatus.ACTIVE
            ]

            if not available_accounts:
                raise AccountPoolError(
                    "没有可用的账号，所有账号均已失效或被禁用",
                    available_count=0,
                )

            # 轮换策略：基于索引选择账号
            # 注意：这里会在available_accounts列表中轮换，而不是在全部accounts中
            # 这样可以自动跳过失效的账号
            pool_size = len(available_accounts)
            index = self._current_index % pool_size
            account = available_accounts[index]

            # 索引前进，下次获取不同的账号
            self._current_index = (self._current_index + 1) % pool_size

            return account

    def mark_account_failed(self, account_id: str) -> None:
        """标记账号失败

        增加账号的失败计数，如果连续失败次数超过阈值则自动禁用。

        Args:
            account_id: 失败的账号ID
        """
        with self._lock:
            # 查找账号
            account = self._find_account_by_id(account_id)
            if account is None:
                return

            # 更新失败计数
            account.fail_count += 1

            # 检查是否超过阈值
            if account.fail_count >= self.auto_disable_threshold:
                # 自动禁用账号
                account.status = AccountStatus.DISABLED

    def mark_account_success(self, account_id: str) -> None:
        """标记账号成功

        重置账号的失败计数（成功后清除之前的失败记录）。

        Args:
            account_id: 成功的账号ID
        """
        with self._lock:
            account = self._find_account_by_id(account_id)
            if account is not None:
                account.fail_count = 0

    def update_usage_stats(self, account_id: str) -> None:
        """更新账号使用统计

        记录账号的使用次数和最后使用时间。

        Args:
            account_id: 账号ID
        """
        with self._lock:
            account = self._find_account_by_id(account_id)
            if account is not None:
                account.used_count += 1
                account.last_used = datetime.now().isoformat()

    def get_available_count(self) -> int:
        """获取当前可用账号数量

        Returns:
            int: 状态为ACTIVE的账号数量
        """
        with self._lock:
            return sum(
                1 for acc in self.accounts if acc.status == AccountStatus.ACTIVE
            )

    def get_total_count(self) -> int:
        """获取账号池总账号数量

        Returns:
            int: 所有账号数量（包括禁用的）
        """
        with self._lock:
            return len(self.accounts)

    def get_all_accounts(self) -> List[AccountInfo]:
        """获取所有账号信息（副本）

        Returns:
            List[AccountInfo]: 账号列表的副本
        """
        with self._lock:
            # 返回副本避免外部修改
            return list(self.accounts)

    def add_account(self, account: AccountInfo) -> None:
        """添加新账号到池中

        Args:
            account: 要添加的账号信息

        Raises:
            AccountPoolError: 账号ID已存在
        """
        with self._lock:
            # 检查ID唯一性
            if self._find_account_by_id(account.id) is not None:
                raise AccountPoolError(
                    f"账号ID已存在: {account.id}",
                    account_id=account.id,
                )

            self.accounts.append(account)

    def remove_account(self, account_id: str) -> None:
        """从池中移除账号

        Args:
            account_id: 要移除的账号ID

        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            self.accounts = [acc for acc in self.accounts if acc.id != account_id]
            # 调整索引以防越界
            if self._current_index >= len(self.accounts):
                self._current_index = 0

    def enable_account(self, account_id: str) -> None:
        """手动启用账号

        Args:
            account_id: 账号ID
        """
        with self._lock:
            account = self._find_account_by_id(account_id)
            if account is not None:
                account.status = AccountStatus.ACTIVE
                account.fail_count = 0  # 重置失败计数

    def disable_account(self, account_id: str) -> None:
        """手动禁用账号

        Args:
            account_id: 账号ID
        """
        with self._lock:
            account = self._find_account_by_id(account_id)
            if account is not None:
                account.status = AccountStatus.DISABLED

    def _find_account_by_id(self, account_id: str) -> Optional[AccountInfo]:
        """根据ID查找账号

        Args:
            account_id: 账号ID

        Returns:
            Optional[AccountInfo]: 找到的账号，如果不存在则返回None
        """
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None

    def reset_fail_counts(self) -> None:
        """重置所有账号的失败计数

        用于手动恢复被误禁用的账号。
        """
        with self._lock:
            for account in self.accounts:
                account.fail_count = 0
                if account.status == AccountStatus.DISABLED:
                    account.status = AccountStatus.ACTIVE

    def get_usage_summary(self) -> dict:
        """获取账号池使用摘要

        Returns:
            dict: 包含统计信息的字典
        """
        with self._lock:
            total_downloads = sum(acc.used_count for acc in self.accounts)

            return {
                "total_accounts": len(self.accounts),
                "active_accounts": self.get_available_count(),
                "disabled_accounts": len(self.accounts) - self.get_available_count(),
                "total_downloads": total_downloads,
                "accounts": [
                    {
                        "id": acc.id,
                        "status": acc.status.value if hasattr(acc.status, "value") else acc.status,
                        "used_count": acc.used_count,
                        "fail_count": acc.fail_count,
                        "last_used": acc.last_used,
                    }
                    for acc in self.accounts
                ],
            }
