"""
用户会话管理器
提供智能的用户状态检查和管理功能
"""

import asyncio
from datetime import datetime, timedelta

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from alpha_new.db.ops import get_all_user_ids, get_valid_users
from alpha_new.scripts.update_user_info import update_user_info_with_api
from alpha_new.utils import get_db_session
from alpha_new.utils.config import get_config

console = Console()


class UserSessionManager:
    """用户会话管理器"""

    def __init__(self):
        self._last_check_time: datetime | None = None
        self._valid_users_cache: list[int] = []
        self._config = get_config()

        # 从配置获取参数，提供默认值
        session_config = self._config.user_session
        self._check_interval = timedelta(hours=session_config.check_interval_hours)
        self._cache_duration = timedelta(minutes=session_config.cache_duration_minutes)
        self._min_valid_users = session_config.min_valid_users
        self._max_concurrent = session_config.max_concurrent_checks
        self._smart_threshold = session_config.smart_check_threshold

    async def ensure_valid_users(self, operation_name: str = "此操作") -> list[int]:
        """
        确保有有效用户可用

        Args:
            operation_name: 操作名称，用于显示提示信息

        Returns:
            有效用户ID列表
        """
        try:
            # 1. 快速检查缓存
            if self._is_cache_valid():
                return self._valid_users_cache

            # 2. 检查数据库中的有效用户
            async with get_db_session() as session:
                valid_users = await get_valid_users(session)
                valid_user_ids = [user.id for user in valid_users]

            # 3. 如果有有效用户且最近检查过，直接使用
            if valid_user_ids and self._is_recently_checked():
                self._update_cache(valid_user_ids)
                return valid_user_ids

            # 4. 需要检查用户状态
            console.print(f"[dim]🔍 {operation_name}需要验证用户登录状态...[/dim]")

            if valid_user_ids:
                # 有用户但需要验证状态
                updated_users = await self._smart_user_check(valid_user_ids)
            else:
                # 没有有效用户，需要全量检查
                console.print("[dim]正在检查所有用户...[/dim]")
                async with get_db_session() as session:
                    all_user_ids = await get_all_user_ids(session)

                if not all_user_ids:
                    console.print("[red]❌ 数据库中没有用户，请先添加用户！[/red]")
                    return []

                updated_users = await self._smart_user_check(all_user_ids)

            self._update_cache(updated_users)
            return updated_users

        except Exception as e:
            console.print(f"[red]❌ 用户状态检查失败: {e}[/red]")
            return []

    async def _smart_user_check(self, user_ids: list[int]) -> list[int]:
        """
        智能用户检查：优先检查最可能有效的用户
        """
        if not user_ids:
            return []

        # 如果用户数量少，直接全部检查
        if len(user_ids) <= self._smart_threshold:
            return await self._batch_check_users(user_ids, "检查用户状态")

        # 用户数量多，采用分阶段检查
        console.print(f"[dim]📊 发现{len(user_ids)}个用户，采用智能检查策略...[/dim]")

        # 第一阶段：检查前几个用户
        first_batch = user_ids[: self._smart_threshold]
        console.print(f"[dim]🔍 第一阶段：检查前{len(first_batch)}个用户...[/dim]")
        valid_users = await self._batch_check_users(first_batch, "快速检查")

        if valid_users:
            # 找到有效用户，判断是否继续检查其他用户
            console.print(f"[green]✅ 找到{len(valid_users)}个有效用户[/green]")

            remaining_users = user_ids[self._smart_threshold :]
            if remaining_users:
                console.print(f"[dim]还有{len(remaining_users)}个用户未检查[/dim]")

                # 自动决策：如果有效用户>=最小要求，跳过其他检查
                if len(valid_users) >= self._min_valid_users:
                    console.print("[dim]✨ 有效用户充足，跳过其他用户检查[/dim]")
                    return valid_users

                # 否则继续检查剩余用户
                console.print("[dim]🔍 继续检查其他用户...[/dim]")
                more_valid = await self._batch_check_users(remaining_users, "补充检查")
                valid_users.extend(more_valid)

            return valid_users
        # 前几个都无效，检查所有剩余用户
        console.print("[dim]⚠️ 前几个用户都无效，检查所有用户...[/dim]")
        remaining_users = user_ids[self._smart_threshold :]
        return await self._batch_check_users(remaining_users, "全面检查")

    async def _batch_check_users(
        self, user_ids: list[int], stage_name: str
    ) -> list[int]:
        """
        批量检查用户状态
        """
        if not user_ids:
            return []

        valid_users = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"{stage_name}...", total=len(user_ids))

            # 控制并发数，避免过载
            semaphore = asyncio.Semaphore(self._max_concurrent)

            async def check_one_user(user_id: int) -> int | None:
                async with semaphore:
                    try:
                        await update_user_info_with_api(user_id)
                        progress.advance(task)

                        # 检查更新后的状态
                        async with get_db_session() as session:
                            users = await get_valid_users(session)
                            if any(user.id == user_id for user in users):
                                return user_id
                        return None
                    except Exception:
                        progress.advance(task)
                        # 错误信息只记录到日志文件，不在终端显示
                        return None

            # 并发检查所有用户
            tasks = [check_one_user(uid) for uid in user_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集有效用户
            for result in results:
                if isinstance(result, int):
                    valid_users.append(result)

        if valid_users:
            console.print(
                f"[green]✅ {stage_name}完成，找到{len(valid_users)}个有效用户: {valid_users}[/green]"
            )
        else:
            console.print(f"[dim]❌ {stage_name}完成，未找到有效用户[/dim]")

        return valid_users

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return (
            self._valid_users_cache
            and self._last_check_time
            and datetime.now() - self._last_check_time < self._cache_duration
        )

    def _is_recently_checked(self) -> bool:
        """检查是否最近检查过"""
        return (
            self._last_check_time
            and datetime.now() - self._last_check_time < self._check_interval
        )

    def _update_cache(self, valid_users: list[int]):
        """更新缓存"""
        self._valid_users_cache = valid_users
        self._last_check_time = datetime.now()

    def force_refresh(self):
        """强制刷新（清除缓存）"""
        self._last_check_time = None
        self._valid_users_cache = []
        console.print("[dim]🔄 用户状态缓存已清除，下次使用时将重新检查[/dim]")

    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        return {
            "valid_users": self._valid_users_cache,
            "last_check": self._last_check_time.isoformat()
            if self._last_check_time
            else None,
            "cache_valid": self._is_cache_valid(),
            "recently_checked": self._is_recently_checked(),
        }


# 全局实例
_session_manager = UserSessionManager()


async def ensure_valid_users(operation_name: str = "此操作") -> list[int]:
    """确保有有效用户可用（便捷函数）"""
    return await _session_manager.ensure_valid_users(operation_name)


def force_refresh_users():
    """强制刷新用户状态"""
    _session_manager.force_refresh()


def get_user_cache_info() -> dict:
    """获取用户缓存信息"""
    return _session_manager.get_cache_info()


async def get_random_valid_user(operation_name: str = "此操作") -> int | None:
    """获取一个随机的有效用户ID"""
    valid_users = await ensure_valid_users(operation_name)
    if not valid_users:
        return None

    import random

    return random.choice(valid_users)
