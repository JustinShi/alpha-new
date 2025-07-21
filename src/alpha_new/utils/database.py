"""
统一数据库管理模块
消除重复的数据库连接代码
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..db.models import Base
from .config import get_config, get_database_url
from .exceptions import DatabaseError


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(
        self, db_url: str | None = None, echo: bool = False
    ) -> AsyncEngine:
        """
        初始化数据库连接

        Args:
            db_url: 数据库URL，如果为None则从配置获取
            echo: 是否输出SQL日志

        Returns:
            数据库引擎

        Raises:
            DatabaseError: 数据库初始化失败
        """
        try:
            if not db_url:
                db_url = get_database_url()

            # 🚀 优化：配置数据库连接池
            config = get_config()
            db_config = config.database

            self._engine = create_async_engine(
                db_url,
                echo=echo,
                future=True,
                # 连接池配置
                pool_size=db_config.pool_size,  # 连接池大小
                max_overflow=db_config.max_overflow,  # 最大溢出连接数
                pool_timeout=30,  # 获取连接超时时间
                pool_recycle=3600,  # 连接回收时间（1小时）
                pool_pre_ping=True,  # 连接前ping检查
                # SQLite特定优化
                connect_args={
                    "check_same_thread": False,  # 允许多线程
                    "timeout": 20,  # 数据库锁超时
                }
                if "sqlite" in db_url
                else {},
            )

            # 创建表
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # 创建会话工厂
            self._session_factory = async_sessionmaker(
                self._engine, expire_on_commit=False, class_=AsyncSession
            )

            return self._engine

        except Exception as e:
            raise DatabaseError(f"数据库初始化失败: {e}", operation="initialize")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取数据库会话（上下文管理器）

        Yields:
            数据库会话

        Raises:
            DatabaseError: 会话创建失败
        """
        if not self._session_factory:
            await self.initialize()

        if not self._session_factory:
            raise DatabaseError("数据库未初始化", operation="get_session")

        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise DatabaseError(
                    f"数据库操作失败: {e}", operation="session_operation"
                )

    async def get_engine(self) -> AsyncEngine:
        """
        获取数据库引擎

        Returns:
            数据库引擎
        """
        if not self._engine:
            await self.initialize()

        if not self._engine:
            raise DatabaseError("数据库引擎未初始化", operation="get_engine")

        return self._engine

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# 全局数据库管理器实例
_db_manager = DatabaseManager()


async def init_database(db_url: str | None = None, echo: bool = False) -> AsyncEngine:
    """
    初始化数据库（便捷函数）

    Args:
        db_url: 数据库URL
        echo: 是否输出SQL日志

    Returns:
        数据库引擎
    """
    return await _db_manager.initialize(db_url, echo)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（便捷函数）

    Yields:
        数据库会话
    """
    async with _db_manager.get_session() as session:
        yield session


async def get_db_engine() -> AsyncEngine:
    """
    获取数据库引擎（便捷函数）

    Returns:
        数据库引擎
    """
    return await _db_manager.get_engine()


async def close_database():
    """关闭数据库连接（便捷函数）"""
    await _db_manager.close()


# 向后兼容的函数
async def init_db(db_url: str) -> AsyncEngine:
    """
    向后兼容的数据库初始化函数

    Args:
        db_url: 数据库URL

    Returns:
        数据库引擎
    """
    return await init_database(db_url, echo=False)


class DatabaseContextManager:
    """数据库上下文管理器，用于脚本中的简化使用"""

    def __init__(self, db_url: str | None = None, echo: bool = False):
        self.db_url = db_url
        self.echo = echo
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    async def __aenter__(self):
        """进入上下文"""
        self.engine = await init_database(self.db_url, self.echo)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取会话"""
        if not self.session_factory:
            raise DatabaseError("数据库未初始化", operation="get_session")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise DatabaseError(
                    f"数据库操作失败: {e}", operation="session_operation"
                )


def database_context(
    db_url: str | None = None, echo: bool = False
) -> DatabaseContextManager:
    """
    创建数据库上下文管理器

    Args:
        db_url: 数据库URL
        echo: 是否输出SQL日志

    Returns:
        数据库上下文管理器

    Usage:
        async with database_context() as db:
            async with db.session() as session:
                # 数据库操作
                pass
    """
    return DatabaseContextManager(db_url, echo)


# 便捷的装饰器
def with_database(func):
    """
    数据库装饰器，自动处理数据库连接

    Usage:
        @with_database
        async def my_function(session: AsyncSession):
            # 数据库操作
            pass
    """

    async def wrapper(*args, **kwargs):
        async with get_db_session() as session:
            return await func(session, *args, **kwargs)

    return wrapper
