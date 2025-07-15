"""
Alpha代币信息API客户端
用于获取Alpha代币列表和详细信息
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

from src.alpha_new.models.alpha_token_model import (
    AlphaTokenFilter,
    AlphaTokenInfo,
    AlphaTokenListResponse,
)

# 配置日志
logger = logging.getLogger(__name__)

# API端点
ALPHA_TOKEN_LIST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"


class AlphaTokenClient:
    """Alpha代币信息API客户端"""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cache_duration: int = 300,  # 缓存5分钟
    ) -> None:
        """
        初始化Alpha代币客户端

        Args:
            session: aiohttp客户端会话
            headers: HTTP请求头
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            cache_duration: 缓存持续时间（秒）
        """
        self.session = session
        self.headers = headers or {}
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache_duration = cache_duration

        # 缓存相关
        self._cache: AlphaTokenListResponse | None = None
        self._cache_time: datetime | None = None

        # 统计信息
        self.stats = {
            "requests_count": 0,
            "cache_hits": 0,
            "errors_count": 0,
            "last_request_time": None,
            "last_error_time": None,
        }

        # 确保headers包含必要的字段
        self.headers.setdefault("Accept", "application/json")
        self.headers.setdefault(
            "User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

    async def get_token_list(self, use_cache: bool = True) -> AlphaTokenListResponse:
        """
        获取Alpha代币列表

        Args:
            use_cache: 是否使用缓存

        Returns:
            AlphaTokenListResponse: 代币列表响应

        Raises:
            aiohttp.ClientError: 网络请求错误
            ValueError: 响应数据解析错误
        """
        # 检查缓存
        if use_cache and self._is_cache_valid() and self._cache is not None:
            logger.debug("使用缓存的代币列表数据")
            self.stats["cache_hits"] += 1
            return self._cache

        # 获取新数据
        logger.info("获取Alpha代币列表...")
        response_data = await self._make_request("GET", ALPHA_TOKEN_LIST_URL)

        try:
            # 解析响应数据
            token_response = AlphaTokenListResponse(**response_data)

            # 更新缓存
            self._cache = token_response
            self._cache_time = datetime.now()

            logger.info(f"成功获取 {len(token_response)} 个Alpha代币信息")
            return token_response

        except Exception as e:
            logger.error(f"解析代币列表响应失败: {e}")
            raise ValueError(f"响应数据格式错误: {e}")

    async def get_token_by_symbol(
        self, symbol: str, use_cache: bool = True
    ) -> AlphaTokenInfo | None:
        """
        根据符号获取代币信息

        Args:
            symbol: 代币符号
            use_cache: 是否使用缓存

        Returns:
            AlphaTokenInfo: 代币信息，未找到返回None
        """
        token_list = await self.get_token_list(use_cache=use_cache)
        return token_list.get_token_by_symbol(symbol)

    async def get_tokens_by_chain(
        self, chain_id: str, use_cache: bool = True
    ) -> list[AlphaTokenInfo]:
        """
        根据链ID获取代币列表

        Args:
            chain_id: 链ID
            use_cache: 是否使用缓存

        Returns:
            List[AlphaTokenInfo]: 代币信息列表
        """
        token_list = await self.get_token_list(use_cache=use_cache)
        return token_list.get_tokens_by_chain(chain_id)

    async def search_tokens(
        self, filter_obj: AlphaTokenFilter, use_cache: bool = True
    ) -> list[AlphaTokenInfo]:
        """
        根据过滤条件搜索代币

        Args:
            filter_obj: 过滤条件
            use_cache: 是否使用缓存

        Returns:
            List[AlphaTokenInfo]: 匹配的代币列表
        """
        token_list = await self.get_token_list(use_cache=use_cache)
        return [token for token in token_list.data if filter_obj.matches(token)]

    async def get_token_symbols(self, use_cache: bool = True) -> list[str]:
        """
        获取所有代币符号列表

        Args:
            use_cache: 是否使用缓存

        Returns:
            List[str]: 代币符号列表
        """
        token_list = await self.get_token_list(use_cache=use_cache)
        return token_list.get_token_symbols()

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache = None
        self._cache_time = None
        logger.debug("代币列表缓存已清除")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "cache_valid": self._is_cache_valid(),
            "cache_age_seconds": self._get_cache_age(),
        }

    async def _make_request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Dict[str, Any]: 响应数据

        Raises:
            aiohttp.ClientError: 网络请求错误
        """
        self.stats["requests_count"] += 1
        self.stats["last_request_time"] = datetime.now()

        # 设置请求参数
        request_kwargs = {"headers": self.headers, "timeout": self.timeout, **kwargs}

        # 重试逻辑
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                # 使用外部session或创建临时session
                if self.session:
                    async with self.session.request(
                        method, url, **request_kwargs
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                else:
                    async with aiohttp.ClientSession() as session:
                        async with session.request(
                            method, url, **request_kwargs
                        ) as response:
                            response.raise_for_status()
                            return await response.json()

            except Exception as e:
                last_exception = e
                self.stats["errors_count"] += 1
                self.stats["last_error_time"] = datetime.now()

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)  # 指数退避
                    logger.warning(
                        f"请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}, {delay}秒后重试"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {e}")
                    raise

        # 不应该到达这里，抛出最后一个异常或通用异常
        if last_exception:
            raise last_exception
        raise aiohttp.ClientError("所有重试均失败，但未记录到具体异常")

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache or not self._cache_time:
            return False

        age = (datetime.now() - self._cache_time).total_seconds()
        return age < self.cache_duration

    def _get_cache_age(self) -> int | None:
        """获取缓存年龄（秒）"""
        if not self._cache_time:
            return None
        return int((datetime.now() - self._cache_time).total_seconds())


async def get_alpha_token_list(
    session: aiohttp.ClientSession | None = None,
    headers: dict[str, str] | None = None,
    use_cache: bool = True,
) -> AlphaTokenListResponse:
    """
    便捷函数：获取Alpha代币列表

    Args:
        session: aiohttp客户端会话
        headers: HTTP请求头
        use_cache: 是否使用缓存

    Returns:
        AlphaTokenListResponse: 代币列表响应
    """
    client = AlphaTokenClient(session=session, headers=headers)
    return await client.get_token_list(use_cache=use_cache)


async def get_alpha_token_by_symbol(
    symbol: str,
    session: aiohttp.ClientSession | None = None,
    headers: dict[str, str] | None = None,
    use_cache: bool = True,
) -> AlphaTokenInfo | None:
    """
    便捷函数：根据符号获取代币信息

    Args:
        symbol: 代币符号
        session: aiohttp客户端会话
        headers: HTTP请求头
        use_cache: 是否使用缓存

    Returns:
        AlphaTokenInfo: 代币信息，未找到返回None
    """
    client = AlphaTokenClient(session=session, headers=headers)
    return await client.get_token_by_symbol(symbol, use_cache=use_cache)


if __name__ == "__main__":

    async def test_alpha_token_client() -> None:
        """测试Alpha代币客户端"""
        async with aiohttp.ClientSession() as session:
            client = AlphaTokenClient(session=session)

            # 获取代币列表
            token_list = await client.get_token_list()
            print(f"获取到 {len(token_list)} 个代币")

            # 显示前5个代币
            for i, token in enumerate(token_list.data[:5]):
                print(f"{i+1}. {token}")

            # 搜索特定代币
            if token_list.data:
                first_token = token_list.data[0]
                found_token = await client.get_token_by_symbol(first_token.symbol)
                print(f"找到代币: {found_token}")

            # 显示统计信息
            print(f"客户端统计: {client.get_stats()}")

    asyncio.run(test_alpha_token_client())
