import logging  # 导入 logging 模块

import aiohttp

logger = logging.getLogger(__name__)  # 获取模块 logger

USER_INFO_URL = (
    "https://www.binance.com/bapi/accounts/v1/private/account/user/base-detail"
)


async def get_user_base_detail(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
) -> dict | None:
    """
    获取用户基础信息。
    """
    try:
        async with session.get(
            USER_INFO_URL, headers=headers, cookies=cookies
        ) as response:
            response.raise_for_status()
            return (await response.json()).get("data")
    except Exception as e:
        logger.error(f"获取用户基础信息失败: {e}")  # 使用 logger.error
        return None
