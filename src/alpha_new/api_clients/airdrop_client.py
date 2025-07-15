import logging  # 导入 logging 模块

import aiohttp

logger = logging.getLogger(__name__)  # 获取模块 logger

# 查询空投列表API
AIRDROP_LIST_URL = "https://www.binance.com/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop"
# 领取空投API
AIRDROP_CLAIM_URL = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop"


async def query_airdrop_list(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None = None,
    page: int = 1,
    rows: int = 50,
) -> dict | None:
    """
    查询空投列表。
    :param session: aiohttp.ClientSession(已配置代理)
    :param headers: 请求头
    :param cookies: 可选,cookies
    :param page: 页码
    :param rows: 每页数量
    :return: 空投列表数据或None
    """
    payload = {"page": page, "rows": rows}
    try:
        async with session.post(
            AIRDROP_LIST_URL, headers=headers, cookies=cookies, json=payload
        ) as response:
            response.raise_for_status()
            return (await response.json()).get("data")
    except Exception as e:
        logger.error(f"查询空投列表失败: {e}")  # 使用 logger.error
        return None


async def claim_airdrop(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
    config_id: str,
) -> dict | None:
    """
    领取指定空投。
    :param session: aiohttp.ClientSession(已配置代理)
    :param headers: 请求头
    :param cookies: 可选,cookies
    :param config_id: 空投配置ID
    :return: 领取结果或None
    """
    payload = {"configId": config_id}
    try:
        async with session.post(
            AIRDROP_CLAIM_URL, headers=headers, cookies=cookies, json=payload
        ) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        logger.error(f"领取空投失败: {e}")  # 使用 logger.error
        return None
