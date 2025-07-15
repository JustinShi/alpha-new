"""
Alpha代币信息服务层
提供高级的Alpha代币信息管理和查询功能
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import aiohttp

from src.alpha_new.api_clients.alpha_token_client import (
    AlphaTokenClient,
)
from src.alpha_new.models.alpha_token_model import (
    AlphaTokenFilter,
    AlphaTokenInfo,
    AlphaTokenListResponse,
)
from src.alpha_new.utils.async_proxy_pool import AsyncProxyPool

# 配置日志
logger = logging.getLogger(__name__)

# 代理文件路径
PROXY_FILE_PATH = "config/proxies.txt"


class AlphaTokenService:
    """Alpha代币信息服务"""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        headers: dict[str, str] | None = None,
        use_proxy: bool = False,
        cache_duration: int = 300,
    ) -> None:
        """
        初始化Alpha代币服务

        Args:
            session: aiohttp客户端会话
            headers: HTTP请求头
            use_proxy: 是否使用代理
            cache_duration: 缓存持续时间（秒）
        """
        self.session = session
        self.headers = headers or {}
        self.use_proxy = use_proxy
        self.cache_duration = cache_duration

        # 代理池管理器
        self._proxy_pool: AsyncProxyPool | None = None

        # Alpha代币客户端
        self.client = AlphaTokenClient(
            session=session, headers=headers, cache_duration=cache_duration
        )

        # 本地缓存和索引
        self._token_by_symbol: dict[str, AlphaTokenInfo] = {}
        self._tokens_by_chain: dict[str, list[AlphaTokenInfo]] = defaultdict(list)
        self._all_chains: set[str] = set()
        self._last_update: datetime | None = None

        # 统计信息
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "last_update_time": None,
            "unique_symbols_queried": set(),
            "unique_chains_queried": set(),
        }

    async def initialize(self) -> None:
        """初始化服务（加载代理池等）"""
        if self.use_proxy:
            try:
                self._proxy_pool = await AsyncProxyPool.from_file(PROXY_FILE_PATH)
                logger.info(f"已加载 {await self._proxy_pool.count()} 个代理")
            except Exception as e:
                logger.warning(f"加载代理池失败: {e}")
                self.use_proxy = False

    async def get_all_tokens(
        self, force_refresh: bool = False
    ) -> AlphaTokenListResponse:
        """
        获取所有Alpha代币信息

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            AlphaTokenListResponse: 代币列表响应
        """
        self.stats["total_queries"] += 1

        # 获取代币列表
        if force_refresh:
            self.client.clear_cache()

        token_response = await self.client.get_token_list(use_cache=not force_refresh)

        # 更新本地索引
        await self._update_local_index(token_response)

        self.stats["api_calls"] += 1
        self.stats["last_update_time"] = datetime.now()

        return token_response

    async def get_token_info(
        self, symbol: str, force_refresh: bool = False
    ) -> AlphaTokenInfo | None:
        """
        获取指定符号的代币信息

        Args:
            symbol: 代币符号
            force_refresh: 是否强制刷新缓存

        Returns:
            AlphaTokenInfo: 代币信息，未找到返回None
        """
        self.stats["total_queries"] += 1
        self.stats["unique_symbols_queried"].add(symbol.upper())

        # 检查本地缓存
        if not force_refresh and symbol.upper() in self._token_by_symbol:
            self.stats["cache_hits"] += 1
            return self._token_by_symbol[symbol.upper()]

        # 从API获取
        token_info = await self.client.get_token_by_symbol(
            symbol, use_cache=not force_refresh
        )

        if token_info:
            # 更新本地缓存
            self._token_by_symbol[symbol.upper()] = token_info

        return token_info

    async def get_tokens_by_chain(
        self, chain_id: str, force_refresh: bool = False
    ) -> list[AlphaTokenInfo]:
        """
        获取指定链上的所有代币

        Args:
            chain_id: 链ID
            force_refresh: 是否强制刷新缓存

        Returns:
            List[AlphaTokenInfo]: 代币信息列表
        """
        self.stats["total_queries"] += 1
        self.stats["unique_chains_queried"].add(chain_id)

        # 检查本地缓存
        if not force_refresh and chain_id in self._tokens_by_chain:
            self.stats["cache_hits"] += 1
            return self._tokens_by_chain[chain_id]

        # 从API获取
        tokens = await self.client.get_tokens_by_chain(
            chain_id, use_cache=not force_refresh
        )

        # 更新本地缓存
        self._tokens_by_chain[chain_id] = tokens

        return tokens

    async def search_tokens(
        self,
        symbol_pattern: str | None = None,
        chain_id: str | None = None,
        min_supply: float | None = None,
        max_supply: float | None = None,
        force_refresh: bool = False,
    ) -> list[AlphaTokenInfo]:
        """
        搜索符合条件的代币

        Args:
            symbol_pattern: 符号模式（支持模糊匹配）
            chain_id: 链ID
            min_supply: 最小供应量
            max_supply: 最大供应量
            force_refresh: 是否强制刷新缓存

        Returns:
            List[AlphaTokenInfo]: 匹配的代币列表
        """
        self.stats["total_queries"] += 1

        # 创建过滤器
        filter_obj = AlphaTokenFilter(
            chain_id=chain_id,
            symbol_pattern=symbol_pattern,
            min_supply=min_supply,
            max_supply=max_supply,
        )

        # 搜索代币
        return await self.client.search_tokens(filter_obj, use_cache=not force_refresh)

    async def get_chain_summary(
        self, force_refresh: bool = False
    ) -> dict[str, dict[str, Any]]:
        """
        获取各链的代币摘要信息

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            Dict[str, Dict[str, Any]]: 各链的摘要信息
        """
        token_response = await self.get_all_tokens(force_refresh=force_refresh)

        # 按链分组统计
        def create_chain_summary():
            return {
                "token_count": 0,
                "tokens": [],
                "total_supply_sum": 0.0,
                "avg_supply": 0.0,
            }

        chain_summary = defaultdict(create_chain_summary)

        for token in token_response.data:
            chain_id = token.chain_id
            chain_summary[chain_id]["token_count"] += 1
            chain_summary[chain_id]["tokens"].append(token.symbol)

            # 尝试计算供应量统计
            try:
                supply = float(token.total_supply)
                chain_summary[chain_id]["total_supply_sum"] += supply
            except (ValueError, TypeError):
                pass

        # 计算平均供应量
        for chain_id, summary in chain_summary.items():
            if summary["token_count"] > 0:
                summary["avg_supply"] = (
                    summary["total_supply_sum"] / summary["token_count"]
                )

        return dict(chain_summary)

    async def get_popular_tokens(
        self, limit: int = 10, force_refresh: bool = False
    ) -> list[AlphaTokenInfo]:
        """
        获取热门代币（按供应量排序）

        Args:
            limit: 返回数量限制
            force_refresh: 是否强制刷新缓存

        Returns:
            List[AlphaTokenInfo]: 热门代币列表
        """
        token_response = await self.get_all_tokens(force_refresh=force_refresh)

        # 按供应量排序
        sorted_tokens = []
        for token in token_response.data:
            try:
                supply = float(token.total_supply)
                sorted_tokens.append((token, supply))
            except (ValueError, TypeError):
                # 无法解析供应量的代币排在最后
                sorted_tokens.append((token, 0))

        # 按供应量降序排序
        sorted_tokens.sort(key=lambda x: x[1], reverse=True)

        return [token for token, _ in sorted_tokens[:limit]]

    async def batch_get_tokens(
        self, symbols: list[str], force_refresh: bool = False
    ) -> dict[str, AlphaTokenInfo | None]:
        """
        批量获取多个代币信息

        Args:
            symbols: 代币符号列表
            force_refresh: 是否强制刷新缓存

        Returns:
            Dict[str, Optional[AlphaTokenInfo]]: 符号到代币信息的映射
        """
        results = {}

        # 并发获取所有代币信息
        tasks = [self.get_token_info(symbol, force_refresh) for symbol in symbols]
        token_infos = await asyncio.gather(*tasks, return_exceptions=True)

        # 组装结果
        for symbol, token_info in zip(symbols, token_infos, strict=False):
            if isinstance(token_info, Exception):
                logger.warning(f"获取代币 {symbol} 信息失败: {token_info}")
                results[symbol] = None
            else:
                results[symbol] = token_info

        return results

    def get_service_stats(self) -> dict[str, Any]:
        """获取服务统计信息"""
        client_stats = self.client.get_stats()

        return {
            "service_stats": {
                **self.stats,
                "unique_symbols_count": len(self.stats["unique_symbols_queried"]),
                "unique_chains_count": len(self.stats["unique_chains_queried"]),
                "local_cache_size": len(self._token_by_symbol),
                "chains_cached": len(self._tokens_by_chain),
            },
            "client_stats": client_stats,
            "proxy_pool_stats": {
                "enabled": self.use_proxy,
                "proxy_count": 0 if not self._proxy_pool else None,  # 需要异步调用
            },
        }

    async def clear_all_cache(self) -> None:
        """清除所有缓存"""
        # 清除客户端缓存
        self.client.clear_cache()

        # 清除本地缓存
        self._token_by_symbol.clear()
        self._tokens_by_chain.clear()
        self._all_chains.clear()
        self._last_update = None

        logger.info("已清除所有代币信息缓存")

    async def _update_local_index(self, token_response: AlphaTokenListResponse) -> None:
        """更新本地索引"""
        # 清除旧索引
        self._token_by_symbol.clear()
        self._tokens_by_chain.clear()
        self._all_chains.clear()

        # 重建索引
        for token in token_response.data:
            # 符号索引
            self._token_by_symbol[token.symbol.upper()] = token

            # 链索引
            self._tokens_by_chain[token.chain_id].append(token)
            self._all_chains.add(token.chain_id)

        self._last_update = datetime.now()
        logger.debug(
            f"已更新本地索引: {len(self._token_by_symbol)} 个代币，{len(self._all_chains)} 条链"
        )


# 全局服务实例管理
_global_service: AlphaTokenService | None = None


async def get_alpha_token_service(
    session: aiohttp.ClientSession | None = None,
    headers: dict[str, str] | None = None,
    use_proxy: bool = False,
) -> AlphaTokenService:
    """
    获取全局Alpha代币服务实例

    Args:
        session: aiohttp客户端会话
        headers: HTTP请求头
        use_proxy: 是否使用代理

    Returns:
        AlphaTokenService: 服务实例
    """
    global _global_service

    if _global_service is None:
        _global_service = AlphaTokenService(
            session=session, headers=headers, use_proxy=use_proxy
        )
        await _global_service.initialize()

    return _global_service


# 便捷函数
async def get_token_info_simple(symbol: str) -> AlphaTokenInfo | None:
    """简单的代币信息获取函数"""
    service = await get_alpha_token_service()
    return await service.get_token_info(symbol)


async def search_tokens_simple(symbol_pattern: str) -> list[AlphaTokenInfo]:
    """简单的代币搜索函数"""
    service = await get_alpha_token_service()
    return await service.search_tokens(symbol_pattern=symbol_pattern)


if __name__ == "__main__":

    async def test_alpha_token_service() -> None:
        """测试Alpha代币服务"""
        async with aiohttp.ClientSession() as session:
            service = AlphaTokenService(session=session)
            await service.initialize()

            # 获取所有代币
            all_tokens = await service.get_all_tokens()
            print(f"获取到 {len(all_tokens)} 个代币")

            # 获取链摘要
            chain_summary = await service.get_chain_summary()
            print(f"链摘要: {chain_summary}")

            # 搜索代币
            if all_tokens.data:
                first_symbol = all_tokens.data[0].symbol
                search_results = await service.search_tokens(
                    symbol_pattern=first_symbol[:3]
                )
                print(f"搜索 '{first_symbol[:3]}' 找到 {len(search_results)} 个代币")

            # 显示统计信息
            stats = service.get_service_stats()
            print(f"服务统计: {stats}")

    asyncio.run(test_alpha_token_service())
