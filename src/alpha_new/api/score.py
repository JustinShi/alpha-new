"""
Alpha积分API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class ScoreAPI:
    BASE_URL = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/tge/common/user-score"

    @staticmethod
    async def get_user_score(headers: dict[str, str]) -> dict[str, Any]:
        """
        查询用户Alpha积分
        :param headers: 包含认证信息的请求头
        :return: 积分信息响应
        """
        client = HTTPClientFactory.get_client()
        resp = await client.get(ScoreAPI.BASE_URL, headers=headers)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
