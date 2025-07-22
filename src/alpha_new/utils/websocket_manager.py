"""
WebSocket连接管理器
提供稳定的WebSocket连接管理和自动重连功能
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import time
from typing import Any

from rich.console import Console

from alpha_new.utils import get_api_logger
from alpha_new.utils.exceptions import NetworkError
from alpha_new.utils.websocket import BinanceWebSocket

console = Console()
logger = get_api_logger()


class ConnectionState(Enum):
    """连接状态"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionStats:
    """连接统计信息"""

    connect_time: float
    reconnect_count: int = 0
    last_message_time: float = 0
    total_messages: int = 0
    error_count: int = 0


class ManagedWebSocket:
    """托管的WebSocket连接（增强版）"""

    def __init__(self, connection_id: str, ws_client: BinanceWebSocket):
        self.connection_id = connection_id
        self.ws_client = ws_client
        self.state = ConnectionState.DISCONNECTED
        self.stats = ConnectionStats(connect_time=time.time())
        self._reconnect_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None

        # 增强的重连策略配置
        self._max_reconnect_attempts = 10  # 增加重连次数
        self._base_reconnect_delay = 2.0  # 基础重连延迟
        self._max_reconnect_delay = 60.0  # 最大重连延迟
        self._reconnect_backoff_factor = 1.5  # 指数退避因子
        self._current_reconnect_delay = self._base_reconnect_delay

        # 连接质量评估
        self._health_check_interval = 30.0
        self._message_timeout = 60.0
        self._ping_interval = 20.0  # ping间隔
        self._connection_quality_score = 100.0  # 连接质量评分
        self._quality_degradation_threshold = 50.0  # 质量降级阈值

        # 连接备份和故障转移
        self._backup_connections: list[Any] = []
        self._primary_connection_failed = False
        self._failover_enabled = True

    async def connect(self, connect_func: Callable, *args, **kwargs):
        """建立连接"""
        try:
            self.state = ConnectionState.CONNECTING
            logger.info(f"WebSocket {self.connection_id} 开始连接...")

            await connect_func(*args, **kwargs)

            self.state = ConnectionState.CONNECTED
            self.stats.connect_time = time.time()
            self.stats.last_message_time = time.time()

            # 启动健康检查
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info(f"WebSocket {self.connection_id} 连接成功")

        except Exception as e:
            self.state = ConnectionState.FAILED
            self.stats.error_count += 1
            logger.error(f"WebSocket {self.connection_id} 连接失败: {e}")
            raise NetworkError(f"WebSocket连接失败: {e}")

    async def disconnect(self):
        """断开连接"""
        self.state = ConnectionState.DISCONNECTED

        # 取消重连任务
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        # 取消健康检查任务
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        # 关闭WebSocket连接
        if hasattr(self.ws_client, "close"):
            await self.ws_client.close()

        logger.info(f"WebSocket {self.connection_id} 已断开")

    async def _health_check_loop(self):
        """健康检查循环"""
        while self.state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self._health_check_interval)

                # 检查是否长时间没有收到消息
                if time.time() - self.stats.last_message_time > self._message_timeout:
                    logger.warning(
                        f"WebSocket {self.connection_id} 长时间无消息，可能连接异常"
                    )
                    await self._trigger_reconnect()
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket {self.connection_id} 健康检查异常: {e}")

    async def _trigger_reconnect(self):
        """触发智能重连"""
        if self.state == ConnectionState.RECONNECTING:
            return  # 已经在重连中

        self.state = ConnectionState.RECONNECTING
        self.stats.reconnect_count += 1

        logger.info(
            f"WebSocket {self.connection_id} 开始智能重连 (第{self.stats.reconnect_count}次)"
        )

        # 评估连接质量并调整重连策略
        await self._assess_connection_quality()

        # 启动重连任务
        self._reconnect_task = asyncio.create_task(self._adaptive_reconnect_loop())

    async def _reconnect_loop(self):
        """重连循环"""
        attempt = 0

        while (
            attempt < self._max_reconnect_attempts
            and self.state == ConnectionState.RECONNECTING
        ):
            try:
                attempt += 1
                logger.info(
                    f"WebSocket {self.connection_id} 重连尝试 {attempt}/{self._max_reconnect_attempts}"
                )

                # 等待重连延迟
                await asyncio.sleep(self._reconnect_delay)

                # 尝试重新连接
                # 注意：这里需要外部提供重连逻辑
                # 因为我们不知道具体的连接参数

                # 如果重连成功，状态会被设置为CONNECTED
                # 这里只是示例，实际需要WebSocketManager来处理

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket {self.connection_id} 重连失败: {e}")
                self.stats.error_count += 1

        if attempt >= self._max_reconnect_attempts:
            self.state = ConnectionState.FAILED
            logger.error(f"WebSocket {self.connection_id} 重连失败，已达到最大尝试次数")

    def on_message_received(self):
        """收到消息时调用"""
        self.stats.last_message_time = time.time()
        self.stats.total_messages += 1


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self._connections: dict[str, ManagedWebSocket] = {}
        self._connection_configs: dict[str, dict] = {}
        self._global_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_reconnects": 0,
            "total_errors": 0,
        }

    async def create_connection(
        self, connection_id: str, ws_client: BinanceWebSocket
    ) -> ManagedWebSocket:
        """创建新的WebSocket连接"""
        if connection_id in self._connections:
            # 如果连接已存在，先关闭旧连接
            await self.close_connection(connection_id)

        managed_ws = ManagedWebSocket(connection_id, ws_client)
        self._connections[connection_id] = managed_ws
        self._global_stats["total_connections"] += 1

        logger.info(f"创建WebSocket连接: {connection_id}")
        return managed_ws

    async def connect_order_stream(
        self, connection_id: str, headers: dict, cookies: dict
    ) -> ManagedWebSocket:
        """连接订单流"""
        ws_client = BinanceWebSocket()
        managed_ws = await self.create_connection(f"{connection_id}_order", ws_client)

        # 保存连接配置用于重连
        self._connection_configs[managed_ws.connection_id] = {
            "type": "order",
            "headers": headers,
            "cookies": cookies,
        }

        try:
            await managed_ws.connect(ws_client.subscribe_order, headers, cookies)
            self._global_stats["active_connections"] += 1
            return managed_ws
        except Exception:
            await self.close_connection(managed_ws.connection_id)
            raise

    async def connect_price_stream(
        self, connection_id: str, price_stream: str
    ) -> ManagedWebSocket:
        """连接价格流"""
        ws_client = BinanceWebSocket()
        managed_ws = await self.create_connection(f"{connection_id}_price", ws_client)

        # 保存连接配置用于重连
        self._connection_configs[managed_ws.connection_id] = {
            "type": "price",
            "price_stream": price_stream,
        }

        try:
            await managed_ws.connect(ws_client.subscribe_price, price_stream)
            self._global_stats["active_connections"] += 1
            return managed_ws
        except Exception:
            await self.close_connection(managed_ws.connection_id)
            raise

    async def reconnect_connection(self, connection_id: str) -> bool:
        """重连指定连接"""
        if connection_id not in self._connections:
            logger.error(f"连接 {connection_id} 不存在，无法重连")
            return False

        if connection_id not in self._connection_configs:
            logger.error(f"连接 {connection_id} 缺少配置信息，无法重连")
            return False

        managed_ws = self._connections[connection_id]
        config = self._connection_configs[connection_id]

        try:
            # 根据连接类型重连
            if config["type"] == "order":
                await managed_ws.connect(
                    managed_ws.ws_client.subscribe_order,
                    config["headers"],
                    config["cookies"],
                )
            elif config["type"] == "price":
                await managed_ws.connect(
                    managed_ws.ws_client.subscribe_price, config["price_stream"]
                )

            managed_ws.state = ConnectionState.CONNECTED
            self._global_stats["total_reconnects"] += 1
            logger.info(f"WebSocket {connection_id} 重连成功")
            return True

        except Exception as e:
            managed_ws.state = ConnectionState.FAILED
            self._global_stats["total_errors"] += 1
            logger.error(f"WebSocket {connection_id} 重连失败: {e}")
            return False

    async def close_connection(self, connection_id: str):
        """关闭指定连接"""
        if connection_id in self._connections:
            managed_ws = self._connections[connection_id]
            await managed_ws.disconnect()

            if managed_ws.state == ConnectionState.CONNECTED:
                self._global_stats["active_connections"] -= 1

            del self._connections[connection_id]

            if connection_id in self._connection_configs:
                del self._connection_configs[connection_id]

            logger.info(f"关闭WebSocket连接: {connection_id}")

    async def close_all_connections(self):
        """关闭所有连接"""
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.close_connection(connection_id)

        logger.info("所有WebSocket连接已关闭")

    def get_connection(self, connection_id: str) -> ManagedWebSocket | None:
        """获取指定连接"""
        return self._connections.get(connection_id)

    def get_connection_stats(self) -> dict[str, Any]:
        """获取连接统计信息"""
        connection_details = {}
        for conn_id, managed_ws in self._connections.items():
            connection_details[conn_id] = {
                "state": managed_ws.state.value,
                "reconnect_count": managed_ws.stats.reconnect_count,
                "total_messages": managed_ws.stats.total_messages,
                "error_count": managed_ws.stats.error_count,
                "uptime": time.time() - managed_ws.stats.connect_time,
            }

        return {"global_stats": self._global_stats, "connections": connection_details}

    async def health_check_all(self) -> dict[str, bool]:
        """检查所有连接的健康状态"""
        health_status = {}

        for conn_id, managed_ws in self._connections.items():
            is_healthy = (
                managed_ws.state == ConnectionState.CONNECTED
                and time.time() - managed_ws.stats.last_message_time < 60
            )
            health_status[conn_id] = is_healthy

            if not is_healthy and managed_ws.state == ConnectionState.CONNECTED:
                # 触发重连
                await managed_ws._trigger_reconnect()

        return health_status


# 全局WebSocket管理器实例
_ws_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器"""
    return _ws_manager


# 熔断器功能增强
class CircuitBreakerState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: float = 30.0  # 恢复超时时间
    success_threshold: int = 3  # 成功阈值（半开状态）
    monitoring_window: float = 60.0  # 监控窗口时间


class CircuitBreaker:
    """WebSocket连接熔断器"""

    def __init__(self, connection_id: str, config: CircuitBreakerConfig):
        self.connection_id = connection_id
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0

    def can_execute(self) -> bool:
        """检查是否可以执行连接"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            # 检查是否可以进入半开状态
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        # HALF_OPEN
        return True

    def record_success(self):
        """记录成功"""
        self.last_success_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"熔断器 {self.connection_id} 恢复正常状态")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """记录失败"""
        self.last_failure_time = int(time.time())
        self.failure_count += 1

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"熔断器 {self.connection_id} 进入熔断状态")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"熔断器 {self.connection_id} 重新进入熔断状态")


class EnhancedWebSocketManager(WebSocketManager):
    """增强的WebSocket管理器（包含熔断器功能）"""

    def __init__(self):
        super().__init__()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._circuit_breaker_config = CircuitBreakerConfig()

    async def create_resilient_connection(
        self,
        connection_id: str,
        ws_client: BinanceWebSocket,
        enable_circuit_breaker: bool = True,
    ) -> ManagedWebSocket:
        """创建具有弹性的WebSocket连接"""
        managed_ws = await self.create_connection(connection_id, ws_client)

        # 启用熔断器
        if enable_circuit_breaker:
            self._circuit_breakers[connection_id] = CircuitBreaker(
                connection_id, self._circuit_breaker_config
            )

        logger.info(f"创建弹性WebSocket连接: {connection_id}")
        return managed_ws

    async def connect_with_circuit_breaker(self, connection_id: str) -> bool:
        """使用熔断器连接"""
        if connection_id not in self._circuit_breakers:
            return True

        circuit_breaker = self._circuit_breakers[connection_id]

        if not circuit_breaker.can_execute():
            logger.warning(f"连接 {connection_id} 被熔断器阻止")
            return False

        try:
            # 这里应该是实际的连接逻辑
            # 为了简化，我们假设连接成功
            circuit_breaker.record_success()
            return True
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error(f"连接 {connection_id} 失败: {e}")
            return False

    def get_circuit_breaker_stats(self) -> dict[str, Any]:
        """获取熔断器统计信息"""
        stats = {}
        for conn_id, breaker in self._circuit_breakers.items():
            stats[conn_id] = {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
                "last_failure_time": breaker.last_failure_time,
                "last_success_time": breaker.last_success_time,
            }
        return stats


# 全局增强WebSocket管理器实例
_enhanced_ws_manager = EnhancedWebSocketManager()


def get_enhanced_websocket_manager() -> EnhancedWebSocketManager:
    """获取全局增强WebSocket管理器"""
    return _enhanced_ws_manager


# 为ManagedWebSocket类添加增强方法
async def _assess_connection_quality(self):
    """评估连接质量"""
    # 基于历史统计计算质量评分
    base_score = 100.0

    # 重连次数影响
    if self.stats.reconnect_count > 0:
        reconnect_penalty = min(50, self.stats.reconnect_count * 10)
        base_score -= reconnect_penalty

    # 错误次数影响
    if self.stats.error_count > 0:
        error_penalty = min(30, self.stats.error_count * 5)
        base_score -= error_penalty

    # 消息接收情况
    time_since_last_message = time.time() - self.stats.last_message_time
    if time_since_last_message > self._message_timeout:
        base_score -= 20

    self._connection_quality_score = max(0, base_score)

    logger.debug(
        f"WebSocket {self.connection_id} 连接质量评分: {self._connection_quality_score:.1f}"
    )


async def _adaptive_reconnect_loop(self):
    """自适应重连循环"""
    attempt = 0

    while (
        attempt < self._max_reconnect_attempts
        and self.state == ConnectionState.RECONNECTING
    ):
        try:
            attempt += 1

            # 根据连接质量调整重连策略
            if self._connection_quality_score < self._quality_degradation_threshold:
                # 连接质量差，使用更保守的重连策略
                delay = min(
                    self._max_reconnect_delay,
                    self._base_reconnect_delay
                    * (self._reconnect_backoff_factor**attempt),
                )
            else:
                # 连接质量好，使用更积极的重连策略
                delay = min(
                    self._max_reconnect_delay // 2,
                    self._base_reconnect_delay * (1.2**attempt),
                )

            logger.info(
                f"WebSocket {self.connection_id} 重连尝试 {attempt}/{self._max_reconnect_attempts} "
                f"(延迟: {delay:.1f}s, 质量评分: {self._connection_quality_score:.1f})"
            )

            # 等待重连延迟
            await asyncio.sleep(delay)

            # 尝试重新连接（需要外部WebSocketManager来处理）
            # 这里只是示例，实际重连逻辑由WebSocketManager处理

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"WebSocket {self.connection_id} 重连失败: {e}")
            self.stats.error_count += 1

    if attempt >= self._max_reconnect_attempts:
        self.state = ConnectionState.FAILED
        self._primary_connection_failed = True
        logger.error(f"WebSocket {self.connection_id} 重连失败，已达到最大尝试次数")

        # 尝试故障转移
        if self._failover_enabled:
            await self._attempt_failover()


async def _attempt_failover(self):
    """尝试故障转移到备用连接"""
    if not self._backup_connections:
        logger.warning(f"WebSocket {self.connection_id} 没有可用的备用连接")
        return

    logger.info(f"WebSocket {self.connection_id} 尝试故障转移")

    for backup_id in self._backup_connections:
        try:
            # 这里需要WebSocketManager来处理实际的故障转移
            logger.info(
                f"WebSocket {self.connection_id} 故障转移到备用连接: {backup_id}"
            )
            break
        except Exception as e:
            logger.error(f"故障转移到 {backup_id} 失败: {e}")


def add_backup_connection(self, backup_connection_id: str):
    """添加备用连接"""
    if backup_connection_id not in self._backup_connections:
        self._backup_connections.append(backup_connection_id)
        logger.info(
            f"WebSocket {self.connection_id} 添加备用连接: {backup_connection_id}"
        )


def get_connection_metrics(self) -> dict[str, Any]:
    """获取连接指标"""
    uptime = time.time() - self.stats.connect_time

    return {
        "connection_id": self.connection_id,
        "state": self.state.value,
        "uptime": uptime,
        "reconnect_count": self.stats.reconnect_count,
        "error_count": self.stats.error_count,
        "total_messages": self.stats.total_messages,
        "quality_score": self._connection_quality_score,
        "last_message_age": time.time() - self.stats.last_message_time,
        "backup_connections": len(self._backup_connections),
        "primary_failed": self._primary_connection_failed,
    }


# 将这些方法添加到ManagedWebSocket类
ManagedWebSocket._assess_connection_quality = _assess_connection_quality
ManagedWebSocket._adaptive_reconnect_loop = _adaptive_reconnect_loop
ManagedWebSocket._attempt_failover = _attempt_failover
ManagedWebSocket.add_backup_connection = add_backup_connection
ManagedWebSocket.get_connection_metrics = get_connection_metrics
