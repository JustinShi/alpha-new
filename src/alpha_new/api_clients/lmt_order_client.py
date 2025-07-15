import logging  # 导入 logging 模块

import aiohttp

logger = logging.getLogger(__name__)  # 获取模块 logger

# 下单API(买/卖)
TRADE_ORDER_URL = (
    "https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place"
)


async def place_order(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
    order_payload: dict,
    order_type: str = "LIMIT",
) -> dict | None:
    """
    下单接口(买入/卖出/刷量), 支持限价单。
    :param session: aiohttp.ClientSession(已配置代理)
    :param headers: 请求头
    :param cookies: 可选,cookies
    :param order_payload: 下单参数(需包含baseAsset、quoteAsset、side、price/quantity等)
    :param order_type: 订单类型, 默认'LIMIT'(限价单)
    :return: 下单结果或None
    """
    payload = dict(order_payload)
    payload["type"] = order_type
    try:
        async with session.post(
            TRADE_ORDER_URL, headers=headers, cookies=cookies, json=payload
        ) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        logger.error(f"下单失败: {e}")  # 使用 logger.error
        return None
