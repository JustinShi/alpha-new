"""
空投服务API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class AirdropAPI:
    QUERY_URL = "https://www.binance.com/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop"
    CLAIM_URL = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop"

    @staticmethod
    async def query_airdrop_list(
        headers: dict[str, str], page: int = 1, rows: int = 50
    ) -> dict[str, Any]:
        """
        查询空投列表
        :param headers: 包含认证信息的请求头
        :param page: 页码
        :param rows: 每页数量
        :return: 空投列表响应
        """
        data = {"page": page, "rows": rows}
        client = HTTPClientFactory.get_client()
        resp = await client.post(AirdropAPI.QUERY_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    @staticmethod
    async def claim_airdrop(headers: dict[str, str], config_id: str) -> dict[str, Any]:
        """
        领取空投
        :param headers: 包含认证信息的请求头
        :param config_id: 空投配置ID
        :return: 领取结果响应
        """
        data = {"configId": config_id}
        client = HTTPClientFactory.get_client()
        resp = await client.post(AirdropAPI.CLAIM_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
