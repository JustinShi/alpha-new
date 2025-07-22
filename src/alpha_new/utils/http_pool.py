"""
全局HTTP连接池管理器
提供高效的HTTP连接复用和管理功能
"""

import asyncio
from contextlib import asynccontextmanager
import time
from typing import Any

import httpx
from rich.console import Console

from alpha_new.utils import get_api_logger
from alpha_new.utils.config import get_config
from alpha_new.utils.exceptions import NetworkError

console = Console()
logger = get_api_logger()


class HTTPConnectionPool:
    """HTTP连接池管理器"""

    def __init__(self):
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._client_locks: dict[str, asyncio.Lock] = {}
        self._client_health: dict[str, dict] = {}  # 连接健康状态
        self._client_usage: dict[str, dict] = {}  # 连接使用统计
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "connections_created": 0,
            "connections_closed": 0,
            "total_response_time": 0.0,
            "error_count": 0,
            "health_checks": 0,
            "auto_cleanups": 0,
        }
        self._config = get_config()
        self._cleanup_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None
        self._is_monitoring = False

        # 动态配置参数
        self._max_pool_size = 50
        self._max_connections_per_client = 200
        self._idle_timeout = 300  # 5分钟空闲超时
        self._health_check_interval = 60  # 1分钟健康检查间隔

    async def get_client(
        self,
        client_id: str = "default",
        base_url: str | None = None,
        timeout: float | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> httpx.AsyncClient:
        """
        获取或创建HTTP客户端（增强版）

        Args:
            client_id: 客户端标识符
            base_url: 基础URL
            timeout: 超时时间
            custom_headers: 自定义请求头

        Returns:
            HTTP客户端实例
        """
        # 为每个客户端创建锁
        if client_id not in self._client_locks:
            self._client_locks[client_id] = asyncio.Lock()

        async with self._client_locks[client_id]:
            # 检查是否需要重建客户端
            if client_id in self._clients:
                if await self._should_recreate_client(client_id):
                    await self._close_client_internal(client_id)
                else:
                    self._stats["cache_hits"] += 1
                    self._update_client_usage(client_id)
                    return self._clients[client_id]

            # 检查连接池大小限制
            if len(self._clients) >= self._max_pool_size:
                await self._cleanup_idle_clients()

            # 创建新的客户端
            client = await self._create_optimized_client(
                client_id, base_url, timeout, custom_headers
            )
            self._clients[client_id] = client
            self._initialize_client_tracking(client_id)
            self._stats["connections_created"] += 1
            logger.debug(f"创建新的HTTP客户端: {client_id}")

            return client

    async def _create_optimized_client(
        self,
        client_id: str,
        base_url: str | None = None,
        timeout: float | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> httpx.AsyncClient:
        """创建优化的HTTP客户端"""

        # 从配置获取默认值
        api_config = self._config.api
        default_timeout = timeout or api_config.timeout

        # 动态调整超时配置
        timeout_config = httpx.Timeout(
            connect=5.0,  # 连接超时
            read=default_timeout,  # 读取超时
            write=10.0,  # 写入超时
            pool=30.0,  # 连接池超时
        )

        # 动态调整连接限制
        limits = httpx.Limits(
            max_keepalive_connections=min(100, self._max_connections_per_client // 2),
            max_connections=self._max_connections_per_client,
            keepalive_expiry=30.0,
        )

        # 构建默认请求头
        default_headers = {
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        if custom_headers:
            default_headers.update(custom_headers)

        # 创建客户端
        client_kwargs = {
            "timeout": timeout_config,
            "limits": limits,
            "headers": default_headers,
            "http2": True,  # 启用HTTP/2
            "follow_redirects": True,  # 自动跟随重定向
            "verify": True,  # 验证SSL证书
        }

        # 只有当base_url不为None时才设置
        if base_url:
            client_kwargs["base_url"] = base_url

        client = httpx.AsyncClient(**client_kwargs)

        logger.info(
            f"创建HTTP客户端 {client_id}: base_url={base_url}, timeout={default_timeout}s"
        )
        return client

    async def _should_recreate_client(self, client_id: str) -> bool:
        """检查是否需要重建客户端"""
        if client_id not in self._client_health:
            return False

        health_info = self._client_health[client_id]

        # 如果连续错误过多，需要重建
        if health_info.get("consecutive_errors", 0) > 3:
            return True

        # 如果客户端创建时间过长，需要重建
        created_at = health_info.get("created_at", 0)
        return time.time() - created_at > 3600  # 1小时

    async def _close_client_internal(self, client_id: str):
        """内部关闭客户端方法"""
        if client_id in self._clients:
            try:
                await self._clients[client_id].aclose()
            except Exception as e:
                logger.warning(f"关闭客户端 {client_id} 时出错: {e}")
            finally:
                del self._clients[client_id]
                if client_id in self._client_health:
                    del self._client_health[client_id]
                if client_id in self._client_usage:
                    del self._client_usage[client_id]
                self._stats["connections_closed"] += 1

    @asynccontextmanager
    async def request(
        self, method: str, url: str, client_id: str = "default", **kwargs
    ):
        """
        执行HTTP请求（上下文管理器）

        Args:
            method: HTTP方法
            url: 请求URL
            client_id: 客户端标识符
            **kwargs: 其他请求参数

        Yields:
            HTTP响应对象
        """
        start_time = time.time()
        client = await self.get_client(client_id)

        try:
            self._stats["total_requests"] += 1

            response = await client.request(method, url, **kwargs)

            # 记录响应时间
            response_time = time.time() - start_time
            self._stats["total_response_time"] += response_time

            logger.debug(
                f"HTTP {method} {url} - {response.status_code} ({response_time:.3f}s)"
            )

            yield response

        except Exception as e:
            self._stats["error_count"] += 1
            logger.error(f"HTTP请求失败 {method} {url}: {e}")
            raise NetworkError(f"HTTP请求失败: {e}")

    async def close_client(self, client_id: str):
        """关闭指定客户端"""
        if client_id in self._clients:
            await self._clients[client_id].aclose()
            del self._clients[client_id]
            self._stats["connections_closed"] += 1
            logger.info(f"关闭HTTP客户端: {client_id}")

    async def close_all(self):
        """关闭所有客户端"""
        for client_id in list(self._clients.keys()):
            await self.close_client(client_id)

        logger.info("所有HTTP客户端已关闭")

    def get_stats(self) -> dict[str, Any]:
        """获取连接池统计信息"""
        avg_response_time = (
            self._stats["total_response_time"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0
        )

        cache_hit_rate = (
            self._stats["cache_hits"] / self._stats["total_requests"] * 100
            if self._stats["total_requests"] > 0
            else 0
        )

        return {
            **self._stats,
            "active_clients": len(self._clients),
            "avg_response_time": avg_response_time,
            "cache_hit_rate": cache_hit_rate,
        }

    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "connections_created": 0,
            "connections_closed": 0,
            "total_response_time": 0.0,
            "error_count": 0,
        }

    def _initialize_client_tracking(self, client_id: str):
        """初始化客户端跟踪信息"""
        self._client_health[client_id] = {
            "created_at": time.time(),
            "consecutive_errors": 0,
            "total_errors": 0,
            "last_error": None,
        }
        self._client_usage[client_id] = {
            "request_count": 0,
            "last_used": time.time(),
            "total_response_time": 0.0,
        }

    def _update_client_usage(self, client_id: str, response_time: float = 0):
        """更新客户端使用统计"""
        if client_id in self._client_usage:
            usage = self._client_usage[client_id]
            usage["request_count"] += 1
            usage["last_used"] = time.time()
            usage["total_response_time"] += response_time

    def _record_client_error(self, client_id: str, error: Exception):
        """记录客户端错误"""
        if client_id in self._client_health:
            health = self._client_health[client_id]
            health["consecutive_errors"] += 1
            health["total_errors"] += 1
            health["last_error"] = str(error)

    def _record_client_success(self, client_id: str):
        """记录客户端成功"""
        if client_id in self._client_health:
            self._client_health[client_id]["consecutive_errors"] = 0

    async def _cleanup_idle_clients(self):
        """清理空闲客户端"""
        current_time = time.time()
        clients_to_remove = []

        for client_id, usage_info in self._client_usage.items():
            if current_time - usage_info.get("last_used", 0) > self._idle_timeout:
                clients_to_remove.append(client_id)

        for client_id in clients_to_remove:
            await self._close_client_internal(client_id)
            logger.debug(f"清理空闲客户端: {client_id}")

        if clients_to_remove:
            self._stats["auto_cleanups"] += 1


# 全局HTTP连接池实例
_http_pool = HTTPConnectionPool()


async def get_http_client(
    client_id: str = "default",
    base_url: str | None = None,
    timeout: float | None = None,
    custom_headers: dict[str, str] | None = None,
) -> httpx.AsyncClient:
    """
    获取HTTP客户端（便捷函数）

    Args:
        client_id: 客户端标识符
        base_url: 基础URL
        timeout: 超时时间
        custom_headers: 自定义请求头

    Returns:
        HTTP客户端实例
    """
    return await _http_pool.get_client(client_id, base_url, timeout, custom_headers)


@asynccontextmanager
async def http_request(method: str, url: str, client_id: str = "default", **kwargs):
    """
    执行HTTP请求（便捷函数）

    Args:
        method: HTTP方法
        url: 请求URL
        client_id: 客户端标识符
        **kwargs: 其他请求参数

    Yields:
        HTTP响应对象
    """
    async with _http_pool.request(method, url, client_id, **kwargs) as response:
        yield response


async def close_http_client(client_id: str):
    """关闭HTTP客户端（便捷函数）"""
    await _http_pool.close_client(client_id)


async def close_all_http_clients():
    """关闭所有HTTP客户端（便捷函数）"""
    await _http_pool.close_all()


def get_http_stats() -> dict[str, Any]:
    """获取HTTP连接池统计信息（便捷函数）"""
    return _http_pool.get_stats()


# 预定义的客户端配置
BINANCE_CLIENT_CONFIG = {
    "client_id": "binance",
    "base_url": "https://www.binance.com",
    "timeout": 30.0,
}

BINANCE_API_CLIENT_CONFIG = {
    "client_id": "binance_api",
    "base_url": "https://api.binance.com",
    "timeout": 10.0,
}

TIME_API_CLIENT_CONFIG = {"client_id": "time_api", "base_url": None, "timeout": 5.0}


async def get_binance_client() -> httpx.AsyncClient:
    """获取币安主站客户端"""
    return await get_http_client(**BINANCE_CLIENT_CONFIG)


async def get_binance_api_client() -> httpx.AsyncClient:
    """获取币安API客户端"""
    return await get_http_client(**BINANCE_API_CLIENT_CONFIG)


async def get_time_api_client() -> httpx.AsyncClient:
    """获取时间API客户端"""
    return await get_http_client(**TIME_API_CLIENT_CONFIG)
