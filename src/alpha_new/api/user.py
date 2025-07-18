"""
用户信息API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class UserAPI:
    BASE_URL = (
        "https://www.binance.com/bapi/accounts/v1/private/account/user/base-detail"
    )

    @staticmethod
    async def get_user_base_detail(headers: dict[str, str]) -> dict[str, Any]:
        """
        获取用户基础信息
        :param headers: 包含认证信息的请求头
        :return: 用户基础信息响应
        """
        client = HTTPClientFactory.get_client()
        resp = await client.post(UserAPI.BASE_URL, headers=headers, json={})
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
