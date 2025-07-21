"""
异步处理优化器
提供高效的异步数据获取和处理功能
"""

import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Any

from rich.console import Console

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.utils import get_api_logger

console = Console()
logger = get_api_logger()


@dataclass
class BatchResult:
    """批量操作结果"""

    success_count: int
    error_count: int
    results: dict[str, Any]
    errors: dict[str, Exception]
    execution_time: float


class AsyncDataFetcher:
    """异步数据获取器"""

    def __init__(self, max_concurrent: int = 10):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_single(self, fetch_func: Callable, *args, **kwargs) -> Any:
        """单个数据获取（带并发控制）"""
        async with self._semaphore:
            return await fetch_func(*args, **kwargs)

    async def fetch_batch(
        self, tasks: list[tuple[str, Callable, tuple, dict]]
    ) -> BatchResult:
        """批量数据获取"""
        start_time = time.time()
        results = {}
        errors = {}

        async def execute_task(task_id: str, func: Callable, args: tuple, kwargs: dict):
            try:
                result = await self.fetch_single(func, *args, **kwargs)
                results[task_id] = result
            except Exception as e:
                errors[task_id] = e
                logger.error(f"批量任务 {task_id} 执行失败: {e}")

        # 创建所有任务
        task_coroutines = [
            execute_task(task_id, func, args, kwargs)
            for task_id, func, args, kwargs in tasks
        ]

        # 并发执行所有任务
        await asyncio.gather(*task_coroutines, return_exceptions=True)

        execution_time = time.time() - start_time

        return BatchResult(
            success_count=len(results),
            error_count=len(errors),
            results=results,
            errors=errors,
            execution_time=execution_time,
        )


class TradingDataProcessor:
    """交易数据处理器"""

    def __init__(self, buffer_size: int = 1000):
        self._price_buffer = deque(maxlen=buffer_size)
        self._volume_buffer = deque(maxlen=buffer_size)
        self._timestamp_buffer = deque(maxlen=buffer_size)
        self._last_update = 0

    def add_price_data(
        self, price: float, volume: float = 0, timestamp: float | None = None
    ):
        """添加价格数据"""
        if timestamp is None:
            timestamp = time.time()

        self._price_buffer.append(price)
        self._volume_buffer.append(volume)
        self._timestamp_buffer.append(timestamp)
        self._last_update = timestamp

    def get_latest_price(self) -> float | None:
        """获取最新价格"""
        return self._price_buffer[-1] if self._price_buffer else None

    def get_price_change(self, period_seconds: int = 60) -> float | None:
        """获取指定时间段内的价格变化"""
        if len(self._price_buffer) < 2:
            return None

        current_time = time.time()
        target_time = current_time - period_seconds

        # 找到目标时间点的价格
        target_price = None
        for i, timestamp in enumerate(self._timestamp_buffer):
            if timestamp >= target_time:
                target_price = self._price_buffer[i]
                break

        if target_price is None:
            return None

        current_price = self._price_buffer[-1]
        return ((current_price - target_price) / target_price) * 100

    def get_moving_average(self, period: int = 10) -> float | None:
        """获取移动平均价格"""
        if len(self._price_buffer) < period:
            return None

        recent_prices = list(self._price_buffer)[-period:]
        return sum(recent_prices) / len(recent_prices)

    def detect_trend(self, period: int = 5) -> str:
        """检测价格趋势"""
        if len(self._price_buffer) < period:
            return "unknown"

        recent_prices = list(self._price_buffer)[-period:]

        # 计算趋势斜率
        x_values = list(range(len(recent_prices)))
        n = len(recent_prices)

        sum_x = sum(x_values)
        sum_y = sum(recent_prices)
        sum_xy = sum(x * y for x, y in zip(x_values, recent_prices, strict=False))
        sum_x2 = sum(x * x for x in x_values)

        # 线性回归斜率
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        if slope > 0.001:
            return "up"
        if slope < -0.001:
            return "down"
        return "stable"


class OptimizedTradingAPI:
    """优化的交易API包装器"""

    def __init__(self, api: AlphaAPI):
        self.api = api
        self._fetcher = AsyncDataFetcher(max_concurrent=5)
        self._last_balance_fetch = 0
        self._balance_cache_duration = 2.0  # 2秒内的余额查询可以复用

    async def get_multiple_balances(self, token_symbols: list[str]) -> dict[str, float]:
        """批量获取多个代币余额（一次API调用）"""
        try:
            data = await self.api.get_wallet_balance()
            balances = {}

            for asset in data.get("data", []):
                symbol = asset.get("asset")
                if symbol in token_symbols:
                    balances[symbol] = float(asset.get("amount", 0))

            # 确保所有请求的代币都有返回值
            for symbol in token_symbols:
                if symbol not in balances:
                    balances[symbol] = 0.0

            return balances

        except Exception as e:
            logger.error(f"批量获取余额失败: {e}")
            return dict.fromkeys(token_symbols, 0.0)

    async def get_trading_data_batch(self, token_symbol: str) -> dict[str, Any]:
        """批量获取交易相关数据"""
        tasks = [
            ("balance", self.api.get_wallet_balance, (), {}),
            ("token_info", self.api.get_token_info, (token_symbol,), {}),
        ]

        result = await self._fetcher.fetch_batch(tasks)

        # 处理余额数据
        balance = 0.0
        if "balance" in result.results:
            balance_data = result.results["balance"]
            for asset in balance_data.get("data", []):
                if asset.get("asset") == token_symbol:
                    balance = float(asset.get("amount", 0))
                    break

        # 处理代币信息
        token_info = result.results.get("token_info", {})

        return {
            "balance": balance,
            "token_info": token_info,
            "execution_time": result.execution_time,
            "success": result.error_count == 0,
        }

    async def execute_order_with_monitoring(
        self, order_func: Callable, *args, **kwargs
    ) -> dict[str, Any]:
        """执行订单并监控结果"""
        start_time = time.time()

        try:
            # 执行订单
            order_result = await order_func(*args, **kwargs)

            if not order_result.get("success"):
                return {
                    "success": False,
                    "error": "订单执行失败",
                    "order_result": order_result,
                    "execution_time": time.time() - start_time,
                }

            order_id = order_result.get("data")
            if not order_id:
                return {
                    "success": False,
                    "error": "未获取到订单ID",
                    "order_result": order_result,
                    "execution_time": time.time() - start_time,
                }

            return {
                "success": True,
                "order_id": order_id,
                "order_result": order_result,
                "execution_time": time.time() - start_time,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }


class TradingPerformanceMonitor:
    """交易性能监控器"""

    def __init__(self):
        self._api_call_times = deque(maxlen=100)
        self._order_execution_times = deque(maxlen=50)
        self._websocket_latencies = deque(maxlen=100)
        self._error_counts = {"api": 0, "websocket": 0, "order": 0}

    def record_api_call(self, duration: float):
        """记录API调用时间"""
        self._api_call_times.append(duration)

    def record_order_execution(self, duration: float):
        """记录订单执行时间"""
        self._order_execution_times.append(duration)

    def record_websocket_latency(self, latency: float):
        """记录WebSocket延迟"""
        self._websocket_latencies.append(latency)

    def record_error(self, error_type: str):
        """记录错误"""
        if error_type in self._error_counts:
            self._error_counts[error_type] += 1

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        stats = {
            "api_calls": {
                "count": len(self._api_call_times),
                "avg_time": sum(self._api_call_times) / len(self._api_call_times)
                if self._api_call_times
                else 0,
                "max_time": max(self._api_call_times) if self._api_call_times else 0,
                "min_time": min(self._api_call_times) if self._api_call_times else 0,
            },
            "order_executions": {
                "count": len(self._order_execution_times),
                "avg_time": sum(self._order_execution_times)
                / len(self._order_execution_times)
                if self._order_execution_times
                else 0,
                "max_time": max(self._order_execution_times)
                if self._order_execution_times
                else 0,
                "min_time": min(self._order_execution_times)
                if self._order_execution_times
                else 0,
            },
            "websocket": {
                "count": len(self._websocket_latencies),
                "avg_latency": sum(self._websocket_latencies)
                / len(self._websocket_latencies)
                if self._websocket_latencies
                else 0,
                "max_latency": max(self._websocket_latencies)
                if self._websocket_latencies
                else 0,
                "min_latency": min(self._websocket_latencies)
                if self._websocket_latencies
                else 0,
            },
            "errors": self._error_counts.copy(),
        }

        return stats

    def get_health_score(self) -> float:
        """获取系统健康评分（0-100）"""
        score = 100.0

        # API调用性能评分
        if self._api_call_times:
            avg_api_time = sum(self._api_call_times) / len(self._api_call_times)
            if avg_api_time > 1.0:  # 超过1秒
                score -= 20
            elif avg_api_time > 0.5:  # 超过0.5秒
                score -= 10

        # 订单执行性能评分
        if self._order_execution_times:
            avg_order_time = sum(self._order_execution_times) / len(
                self._order_execution_times
            )
            if avg_order_time > 5.0:  # 超过5秒
                score -= 30
            elif avg_order_time > 2.0:  # 超过2秒
                score -= 15

        # WebSocket延迟评分
        if self._websocket_latencies:
            avg_ws_latency = sum(self._websocket_latencies) / len(
                self._websocket_latencies
            )
            if avg_ws_latency > 0.1:  # 超过100ms
                score -= 15
            elif avg_ws_latency > 0.05:  # 超过50ms
                score -= 5

        # 错误率评分
        total_operations = len(self._api_call_times) + len(self._order_execution_times)
        if total_operations > 0:
            total_errors = sum(self._error_counts.values())
            error_rate = total_errors / total_operations
            if error_rate > 0.1:  # 错误率超过10%
                score -= 25
            elif error_rate > 0.05:  # 错误率超过5%
                score -= 10

        return max(0.0, score)


# 全局性能监控器
_performance_monitor = TradingPerformanceMonitor()


def get_performance_monitor() -> TradingPerformanceMonitor:
    """获取全局性能监控器"""
    return _performance_monitor
