"""
用户服务层
负责用户相关业务逻辑, 如headers/cookies有效性检测等。
"""

import aiohttp

from src.alpha_new.api_clients.user_client import get_user_base_detail
from src.alpha_new.models.user_model import UserBaseDetailModel


async def check_user_headers_cookies(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None = None,
) -> UserBaseDetailModel:
    """
    检查headers和cookies有效性, 返回UserBaseDetailModel。
    :param session: aiohttp.ClientSession(已配置代理)
    :param headers: 请求头
    :param cookies: 可选,cookies
    :return: UserBaseDetailModel, 包含firstName、email、success字段
    """
    data = await get_user_base_detail(session, headers, cookies)
    model = UserBaseDetailModel()
    if data:
        model.firstName = data.get("firstName")
        model.email = data.get("email")
        model.success = bool(model.firstName and model.email)
    else:
        model.success = False
    return model
