"""
钱包余额API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class WalletAPI:
    BASE_URL = (
        "https://www.binance.com/bapi/asset/v2/private/asset-service/wallet/asset"
    )

    @staticmethod
    async def get_wallet_balance(
        headers: dict[str, str], quote_asset: str = "USDT", need_alpha_asset: int = 1
    ) -> dict[str, Any]:
        """
        查询钱包余额
        :param headers: 包含认证信息的请求头
        :param quote_asset: 计价资产,默认USDT
        :param need_alpha_asset: 是否需要Alpha资产,1为需要
        :return: 钱包余额响应
        """
        params = {"needAlphaAsset": str(need_alpha_asset), "quoteAsset": quote_asset}
        client = HTTPClientFactory.get_client()
        resp = await client.get(WalletAPI.BASE_URL, headers=headers, params=params)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
