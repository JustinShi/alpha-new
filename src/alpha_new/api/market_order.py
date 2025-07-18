"""
市价订单API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class MarketAPI:
    QUOTE_URL = (
        "https://www.binance.com/bapi/defi/v1/private/wallet-direct/swap/cex/get-quote"
    )
    BUY_URL = "https://www.binance.com/bapi/defi/v2/private/wallet-direct/swap/cex/buy/pre/payment"
    SELL_URL = "https://www.binance.com/bapi/defi/v2/private/wallet-direct/swap/cex/sell/pre/payment"

    @staticmethod
    async def get_quote(
        headers: dict[str, str],
        from_asset: str,
        to_asset: str,
        from_amount: str,
        slippage: str = "0.5",
    ) -> dict[str, Any]:
        """
        获取市价报价
        """
        data = {
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": from_amount,
            "slippage": slippage,
        }
        client = HTTPClientFactory.get_client()
        resp = await client.post(MarketAPI.QUOTE_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    @staticmethod
    async def buy(
        headers: dict[str, str],
        quote_id: str,
        from_asset: str,
        to_asset: str,
        from_amount: str,
        slippage: str = "0.5",
    ) -> dict[str, Any]:
        """
        执行市价买入订单
        """
        data = {
            "quoteId": quote_id,
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": from_amount,
            "slippage": slippage,
        }
        client = HTTPClientFactory.get_client()
        resp = await client.post(MarketAPI.BUY_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    @staticmethod
    async def sell(
        headers: dict[str, str],
        quote_id: str,
        from_asset: str,
        to_asset: str,
        from_amount: str,
        slippage: str = "0.5",
    ) -> dict[str, Any]:
        """
        执行市价卖出订单
        """
        data = {
            "quoteId": quote_id,
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": from_amount,
            "slippage": slippage,
        }
        client = HTTPClientFactory.get_client()
        resp = await client.post(MarketAPI.SELL_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
