"""
市价订单客户端
提供市价报价查询和市价下单功能
包含错误处理、重试机制、数据验证等优化功能
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, field_validator

# 配置日志
logger = logging.getLogger(__name__)

# API端点
MARKET_QUOTE_URL = (
    "https://www.binance.com/bapi/asset/v1/private/alpha-trade/market-quote"
)
MARKET_ORDER_URL = (
    "https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place"
)


class OrderSide(str, Enum):
    """订单方向枚举"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型枚举"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


class MarketQuoteRequest(BaseModel):
    """市价报价请求模型"""

    symbol: str = Field(..., description="交易对符号")
    side: OrderSide = Field(..., description="订单方向")
    quantity: float = Field(..., gt=0, description="交易数量")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("交易对符号不能为空")
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("交易数量必须大于0")
        return v


class MarketOrderRequest(BaseModel):
    """市价下单请求模型"""

    symbol: str = Field(..., description="交易对符号")
    side: OrderSide = Field(..., description="订单方向")
    quantity: float = Field(..., gt=0, description="交易数量")
    type: OrderType = Field(default=OrderType.MARKET, description="订单类型")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("交易对符号不能为空")
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("交易数量必须大于0")
        return v


class MarketQuoteResponse(BaseModel):
    """市价报价响应模型"""

    symbol: str
    side: str
    quantity: float
    price: float | None = None
    amount: float | None = None
    fee: float | None = None
    timestamp: int | None = None


class MarketOrderResponse(BaseModel):
    """市价下单响应模型"""

    orderId: str | None = None
    symbol: str
    side: str
    quantity: float
    price: float | None = None
    status: str | None = None
    timestamp: int | None = None


@dataclass
class OrderResult:
    """订单结果"""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    response_time: float | None = None
    retry_count: int = 0


class MarketOrderClient:
    """市价订单客户端"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        headers: dict[str, str],
        cookies: dict[str, str] | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """
        初始化市价订单客户端

        Args:
            session: aiohttp会话
            headers: 请求头
            cookies: 请求cookies
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            timeout: 请求超时时间(秒)
        """
        self.session = session
        self.headers = headers
        self.cookies = cookies or {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # 统计信息
        self.stats = {
            "quote_requests": 0,
            "quote_success": 0,
            "quote_errors": 0,
            "order_requests": 0,
            "order_success": 0,
            "order_errors": 0,
            "total_retries": 0,
            "avg_response_time": 0.0,
        }

        # 响应时间记录
        self._response_times: list[float] = []

    async def _make_request(
        self, url: str, payload: dict[str, Any], operation: str
    ) -> OrderResult:
        """
        发送HTTP请求（带重试机制）

        Args:
            url: 请求URL
            payload: 请求载荷
            operation: 操作名称（用于日志）

        Returns:
            OrderResult: 请求结果
        """
        start_time = datetime.now()

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"[{operation}] 第{attempt + 1}次尝试: {payload}")

                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with self.session.post(
                    url,
                    headers=self.headers,
                    cookies=self.cookies,
                    json=payload,
                    timeout=timeout,
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    self._response_times.append(response_time)

                    # 更新平均响应时间
                    if self._response_times:
                        self.stats["avg_response_time"] = sum(
                            self._response_times
                        ) / len(self._response_times)

                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[{operation}] 请求成功: {response.status}")
                        return OrderResult(
                            success=True,
                            data=data,
                            response_time=response_time,
                            retry_count=attempt,
                        )
                    error_text = await response.text()
                    logger.warning(
                        f"[{operation}] HTTP错误 {response.status}: {error_text}"
                    )

                    # 某些错误不需要重试
                    if response.status in [400, 401, 403, 404]:
                        return OrderResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}",
                            response_time=response_time,
                            retry_count=attempt,
                        )

                    # 其他错误进行重试
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (2**attempt))  # 指数退避
                        self.stats["total_retries"] += 1
                        continue
                    return OrderResult(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        response_time=response_time,
                        retry_count=attempt,
                    )

            except TimeoutError:
                logger.error(f"[{operation}] 请求超时")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    self.stats["total_retries"] += 1
                    continue
                return OrderResult(success=False, error="请求超时", retry_count=attempt)

            except Exception as e:
                logger.error(f"[{operation}] 请求异常: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    self.stats["total_retries"] += 1
                    continue
                return OrderResult(success=False, error=str(e), retry_count=attempt)

        return OrderResult(
            success=False, error="达到最大重试次数", retry_count=self.max_retries
        )

    async def get_market_quote(
        self, symbol: str, side: OrderSide, quantity: float
    ) -> OrderResult:
        """
        获取市价报价

        Args:
            symbol: 交易对符号
            side: 订单方向
            quantity: 交易数量

        Returns:
            OrderResult: 报价结果
        """
        self.stats["quote_requests"] += 1

        try:
            # 数据验证
            request = MarketQuoteRequest(symbol=symbol, side=side, quantity=quantity)

            # 发送请求
            result = await self._make_request(
                MARKET_QUOTE_URL, request.dict(), "获取市价报价"
            )

            if result.success:
                self.stats["quote_success"] += 1
                # 解析响应数据
                if result.data and "data" in result.data:
                    quote_data = result.data["data"]
                    result.data = MarketQuoteResponse(**quote_data).dict()
            else:
                self.stats["quote_errors"] += 1

            return result

        except Exception as e:
            self.stats["quote_errors"] += 1
            logger.error(f"获取市价报价失败: {e}")
            return OrderResult(success=False, error=f"数据验证失败: {e}")

    async def place_market_order(
        self, symbol: str, side: OrderSide, quantity: float
    ) -> OrderResult:
        """
        市价下单

        Args:
            symbol: 交易对符号
            side: 订单方向
            quantity: 交易数量

        Returns:
            OrderResult: 下单结果
        """
        self.stats["order_requests"] += 1

        try:
            # 数据验证
            request = MarketOrderRequest(
                symbol=symbol, side=side, quantity=quantity, type=OrderType.MARKET
            )

            # 发送请求
            result = await self._make_request(
                MARKET_ORDER_URL, request.dict(), f"市价{side.value}单下单"
            )

            if result.success:
                self.stats["order_success"] += 1
                # 解析响应数据
                if result.data:
                    try:
                        order_data = result.data
                        if "data" in order_data:
                            order_data = order_data["data"]
                        result.data = MarketOrderResponse(**order_data).dict()
                    except Exception as e:
                        logger.warning(
                            f"解析订单响应失败: {e}, 原始数据: {result.data}"
                        )
            else:
                self.stats["order_errors"] += 1

            return result

        except Exception as e:
            self.stats["order_errors"] += 1
            logger.error(f"市价下单失败: {e}")
            return OrderResult(success=False, error=f"数据验证失败: {e}")

    async def place_market_buy_order(self, symbol: str, quantity: float) -> OrderResult:
        """
        市价买单

        Args:
            symbol: 交易对符号
            quantity: 买入数量

        Returns:
            OrderResult: 下单结果
        """
        return await self.place_market_order(symbol, OrderSide.BUY, quantity)

    async def place_market_sell_order(
        self, symbol: str, quantity: float
    ) -> OrderResult:
        """
        市价卖单

        Args:
            symbol: 交易对符号
            quantity: 卖出数量

        Returns:
            OrderResult: 下单结果
        """
        return await self.place_market_order(symbol, OrderSide.SELL, quantity)

    async def get_quote_and_order(
        self, symbol: str, side: OrderSide, quantity: float, confirm_quote: bool = True
    ) -> tuple[OrderResult, OrderResult | None]:
        """
        获取报价并下单（组合操作）

        Args:
            symbol: 交易对符号
            side: 订单方向
            quantity: 交易数量
            confirm_quote: 是否确认报价后再下单

        Returns:
            tuple: (报价结果, 下单结果)
        """
        # 获取报价
        quote_result = await self.get_market_quote(symbol, side, quantity)

        if not quote_result.success:
            logger.error(f"获取报价失败: {quote_result.error}")
            return quote_result, None

        if confirm_quote:
            logger.info(f"报价信息: {quote_result.data}")
            # 这里可以添加报价确认逻辑

        # 下单
        order_result = await self.place_market_order(symbol, side, quantity)

        return quote_result, order_result

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["success_rate"] = {
            "quote": (stats["quote_success"] / max(stats["quote_requests"], 1)) * 100,
            "order": (stats["order_success"] / max(stats["order_requests"], 1)) * 100,
        }
        return stats

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "quote_requests": 0,
            "quote_success": 0,
            "quote_errors": 0,
            "order_requests": 0,
            "order_success": 0,
            "order_errors": 0,
            "total_retries": 0,
            "avg_response_time": 0.0,
        }
        self._response_times.clear()


# 向后兼容的函数接口
async def get_market_quote(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
    symbol: str,
    side: str,
    quantity: float,
) -> dict | None:
    """
    获取市价报价（向后兼容接口）
    """
    client = MarketOrderClient(session, headers, cookies)
    result = await client.get_market_quote(symbol, OrderSide(side), quantity)
    return result.data if result.success else None


async def place_market_order(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
    symbol: str,
    side: str,
    quantity: float,
) -> dict | None:
    """
    市价下单（向后兼容接口）
    """
    client = MarketOrderClient(session, headers, cookies)
    result = await client.place_market_order(symbol, OrderSide(side), quantity)
    return result.data if result.success else None
