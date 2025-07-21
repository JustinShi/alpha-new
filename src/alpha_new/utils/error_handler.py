import asyncio
from collections.abc import Callable
from enum import Enum
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""

    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_ORDER = "INVALID_ORDER"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    WEBSOCKET_DISCONNECT = "WEBSOCKET_DISCONNECT"
    API_ERROR = "API_ERROR"
    UNKNOWN = "UNKNOWN"


class ErrorHandler:
    """错误分类处理器"""

    # 错误关键词映射
    ERROR_KEYWORDS = {
        ErrorType.INSUFFICIENT_BALANCE: [
            "余额不足",
            "481020",
            "insufficient balance",
            "balance not enough",
        ],
        ErrorType.NETWORK_TIMEOUT: [
            "timeout",
            "连接超时",
            "网络超时",
            "connection timeout",
            "read timeout",
        ],
        ErrorType.RATE_LIMIT: [
            "rate limit",
            "限流",
            "too many requests",
            "429",
            "请求过于频繁",
        ],
        ErrorType.INVALID_ORDER: [
            "invalid order",
            "订单无效",
            "order invalid",
            "参数错误",
        ],
        ErrorType.ORDER_NOT_FOUND: [
            "order not found",
            "订单不存在",
            "order does not exist",
        ],
        ErrorType.WEBSOCKET_DISCONNECT: [
            "connection closed",
            "连接断开",
            "websocket",
            "connection reset",
        ],
        ErrorType.API_ERROR: [
            "api error",
            "服务器错误",
            "internal error",
            "500",
            "502",
            "503",
        ],
    }

    def __init__(self):
        self.error_counts: dict[ErrorType, int] = dict.fromkeys(ErrorType, 0)
        self.last_error_time: dict[ErrorType, float] = dict.fromkeys(ErrorType, 0)
        self.error_handlers: dict[ErrorType, Callable] = {}
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """设置默认错误处理器"""
        self.error_handlers = {
            ErrorType.INSUFFICIENT_BALANCE: self._handle_insufficient_balance,
            ErrorType.NETWORK_TIMEOUT: self._handle_network_timeout,
            ErrorType.RATE_LIMIT: self._handle_rate_limit,
            ErrorType.INVALID_ORDER: self._handle_invalid_order,
            ErrorType.ORDER_NOT_FOUND: self._handle_order_not_found,
            ErrorType.WEBSOCKET_DISCONNECT: self._handle_websocket_disconnect,
            ErrorType.API_ERROR: self._handle_api_error,
            ErrorType.UNKNOWN: self._handle_unknown_error,
        }

    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """分类错误类型"""
        error_msg = str(error).lower()

        for error_type, keywords in ErrorHandler.ERROR_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in error_msg:
                    return error_type

        return ErrorType.UNKNOWN

    def record_error(self, error_type: ErrorType):
        """记录错误统计"""
        self.error_counts[error_type] += 1
        self.last_error_time[error_type] = time.time()

    def get_error_stats(self) -> dict[str, Any]:
        """获取错误统计信息"""
        stats = {}
        for error_type in ErrorType:
            stats[error_type.value] = {
                "count": self.error_counts[error_type],
                "last_time": self.last_error_time[error_type],
                "time_since_last": time.time() - self.last_error_time[error_type]
                if self.last_error_time[error_type] > 0
                else None,
            }
        return stats

    async def handle_error(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理错误并返回处理结果"""
        error_type = self.classify_error(error)
        self.record_error(error_type)

        logger.warning(f"用户{user_id}发生{error_type.value}错误: {error}")

        # 调用对应的错误处理器
        handler = self.error_handlers.get(error_type, self._handle_unknown_error)
        result = await handler(error, user_id, context)

        return {
            "error_type": error_type.value,
            "error_message": str(error),
            "user_id": user_id,
            "context": context,
            "handled": result.get("handled", False),
            "action": result.get("action", "none"),
            "retry_after": result.get("retry_after", 0),
        }

    async def _handle_insufficient_balance(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理余额不足错误"""
        logger.info(f"用户{user_id}余额不足，触发自动卖出逻辑")
        return {"handled": True, "action": "auto_sell", "retry_after": 0}

    async def _handle_network_timeout(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理网络超时错误"""
        logger.warning(f"用户{user_id}网络超时，建议重试")
        return {
            "handled": True,
            "action": "retry",
            "retry_after": 5,  # 5秒后重试
        }

    async def _handle_rate_limit(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理API限流错误"""
        logger.warning(f"用户{user_id}触发API限流，需要等待")
        return {
            "handled": True,
            "action": "wait",
            "retry_after": 60,  # 1分钟后重试
        }

    async def _handle_invalid_order(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理无效订单错误"""
        logger.error(f"用户{user_id}订单参数无效: {error}")
        return {"handled": True, "action": "skip", "retry_after": 0}

    async def _handle_order_not_found(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理订单不存在错误"""
        logger.warning(f"用户{user_id}订单不存在，可能已成交或被撤销")
        return {"handled": True, "action": "check_status", "retry_after": 0}

    async def _handle_websocket_disconnect(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理WebSocket断开错误"""
        logger.warning(f"用户{user_id}WebSocket连接断开，将自动重连")
        return {
            "handled": True,
            "action": "reconnect",
            "retry_after": 2,  # 2秒后重连
        }

    async def _handle_api_error(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理API服务器错误"""
        logger.error(f"用户{user_id}API服务器错误: {error}")
        return {
            "handled": True,
            "action": "retry",
            "retry_after": 30,  # 30秒后重试
        }

    async def _handle_unknown_error(
        self, error: Exception, user_id: int, context: dict[str, Any]
    ) -> dict[str, Any]:
        """处理未知错误"""
        logger.error(f"用户{user_id}未知错误: {error}")
        return {"handled": False, "action": "log", "retry_after": 0}


class SmartRetry:
    """智能重试机制"""

    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.error_handler = ErrorHandler()

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，支持智能重试"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if attempt == self.max_retries:
                    # 最后一次尝试失败，记录错误并抛出
                    await self.error_handler.handle_error(
                        e, 0, {"function": func.__name__}
                    )
                    raise

                # 分类错误并获取重试建议
                context = {
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries,
                }

                result = await self.error_handler.handle_error(e, 0, context)

                if result["action"] == "skip":
                    # 跳过重试
                    raise
                if result["action"] == "wait":
                    # 等待指定时间
                    await asyncio.sleep(result["retry_after"])
                else:
                    # 指数退避重试
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)

        if last_error:
            raise last_error
        return None


# 全局错误处理器实例
global_error_handler = ErrorHandler()
