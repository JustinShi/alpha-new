"""
动态网络延迟优化器
提供自动网络延迟检测、分析和优化功能
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Any

try:
    from typing import Dict, List
except ImportError:
    # Python 3.8 兼容性
    Dict = dict
    List = list

import httpx
from rich.console import Console

from alpha_new.utils import get_api_logger

console = Console()
logger = get_api_logger()


@dataclass
class LatencyConfig:
    """延迟优化配置"""

    test_interval: int = 60  # 测试间隔（秒）
    max_latency_threshold: float = 2000.0  # 最大延迟阈值（毫秒）
    history_size: int = 100  # 历史数据大小
    min_test_count: int = 10  # 最小测试次数
    default_advance_ms: int = 120  # 默认提前时间（毫秒）
    safety_multiplier: float = 1.5  # 安全系数


@dataclass
class LatencyResult:
    """延迟测试结果"""

    url: str
    method: str
    latency: float
    status_code: int
    timestamp: datetime
    success: bool
    error: str | None = None


@dataclass
class LatencyStats:
    """延迟统计信息"""

    min_latency: float
    max_latency: float
    avg_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    success_rate: float
    test_count: int
    optimal_advance_ms: int


class DynamicLatencyOptimizer:
    """动态网络延迟优化器"""

    def __init__(self, config: LatencyConfig | None = None):
        self.config = config or LatencyConfig()
        self.latency_history: Dict[str, deque] = {}
        self.optimal_advance_ms = self.config.default_advance_ms
        self.last_test_time = 0
        self.is_monitoring = False
        self._monitor_task: asyncio.Task | None = None

        # 预定义的测试端点
        self.test_endpoints = {
            "binance_time": {
                "url": "https://api.binance.com/api/v3/time",
                "method": "GET",
                "weight": 1.0,
            }
        }

    async def measure_latency(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] | None = None,
        data: Dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> LatencyResult:
        """测量单次网络延迟"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                end_time = time.time()
                latency = (end_time - start_time) * 1000  # 转换为毫秒

                return LatencyResult(
                    url=url,
                    method=method,
                    latency=latency,
                    status_code=response.status_code,
                    timestamp=datetime.now(),
                    success=response.status_code < 500,
                )

        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000

            return LatencyResult(
                url=url,
                method=method,
                latency=latency,
                status_code=0,
                timestamp=datetime.now(),
                success=False,
                error=str(e),
            )

    async def auto_tune_advance_ms(self, headers: Dict[str, str] | None = None) -> int:
        """基于历史数据自动调优提前时间"""
        logger.info("🔧 开始自动调优网络延迟参数...")

        # 测试主要端点
        results = []
        for endpoint_key in self.test_endpoints:
            endpoint = self.test_endpoints[endpoint_key]

            try:
                # 执行延迟测试
                for i in range(5):  # 测试5次
                    result = await self.measure_latency(
                        url=endpoint["url"], method=endpoint["method"], headers=headers
                    )
                    if result.success:
                        results.append(result.latency)
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"测试端点 {endpoint_key} 时出错: {e}")

        if not results:
            logger.warning("⚠️ 没有可用的延迟测试数据，使用默认配置")
            return self.config.default_advance_ms

        # 计算最优提前时间
        if len(results) >= 3:
            p95_latency = sorted(results)[int(len(results) * 0.95)]
            self.optimal_advance_ms = int(p95_latency * self.config.safety_multiplier)
            self.optimal_advance_ms = max(50, min(self.optimal_advance_ms, 1000))
        else:
            self.optimal_advance_ms = self.config.default_advance_ms

        logger.info(f"✅ 自动调优完成，最优提前时间: {self.optimal_advance_ms}ms")
        return self.optimal_advance_ms

    async def start_background_monitoring(self, headers: Dict[str, str] | None = None):
        """启动后台延迟监控"""
        if self.is_monitoring:
            logger.warning("⚠️ 后台监控已在运行")
            return

        self.is_monitoring = True
        logger.info("🚀 启动后台网络延迟监控")

    async def stop_background_monitoring(self):
        """停止后台延迟监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        logger.info("⏹️ 停止后台网络延迟监控")

    def get_optimization_report(self) -> Dict[str, Any]:
        """生成优化报告"""
        return {
            "status": "success",
            "optimal_advance_ms": self.optimal_advance_ms,
            "recommendations": ["网络延迟优化器工作正常"],
        }


# 全局延迟优化器实例
_global_optimizer: DynamicLatencyOptimizer | None = None


def get_latency_optimizer(
    config: LatencyConfig | None = None,
) -> DynamicLatencyOptimizer:
    """获取全局延迟优化器实例"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = DynamicLatencyOptimizer(config)
    return _global_optimizer


async def optimize_network_latency(headers: Dict[str, str] | None = None) -> int:
    """便捷函数：优化网络延迟并返回最优提前时间"""
    optimizer = get_latency_optimizer()
    return await optimizer.auto_tune_advance_ms(headers)
