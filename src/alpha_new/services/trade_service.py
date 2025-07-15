import logging  # 导入 logging 模块

import aiohttp

from src.alpha_new.api_clients.lmt_order_client import place_order
from src.alpha_new.utils.async_proxy_pool import AsyncProxyPool

logger = logging.getLogger(__name__)  # 获取模块 logger

# 假设代理文件路径
PROXY_FILE_PATH = "config/proxies.txt"


class ProxyPoolManager:
    _instance = None

    @classmethod
    async def get_instance(cls) -> AsyncProxyPool:  # 添加返回类型提示
        if cls._instance is None:
            cls._instance = await AsyncProxyPool.from_file(PROXY_FILE_PATH)
        return cls._instance


async def batch_place_orders(users: list[dict], order_payload: dict) -> None:
    """
    批量下单(卖出/刷量)。
    :param users: 用户信息列表(每项需含headers/cookies)
    :param order_payload: 下单参数模板
    """
    pool = await ProxyPoolManager.get_instance()  # 使用类方法获取实例
    for user in users:
        proxy = user.get("proxy")  # 尝试从用户配置中获取代理
        if not proxy:
            proxy = await pool.get_random()  # 如果用户配置中没有, 则从代理池获取

        async with aiohttp.ClientSession(proxy=proxy) as session:  # 使用代理创建session
            result = await place_order(
                session, user["headers"], user.get("cookies"), order_payload
            )
            logger.info(
                f"用户 {user.get('name', '')} 下单结果: {result}"
            )  # 使用 logger.info
