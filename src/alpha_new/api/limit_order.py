"""
限价订单API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class LimitOrderAPI:
    PLACE_URL = "https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/place"
    CANCEL_URL = (
        "https://www.binance.com/bapi/asset/v1/private/alpha-trade/order/cancel"
    )

    @staticmethod
    async def place_order(
        headers: dict[str, str],
        base_asset: str,
        quote_asset: str,
        side: str,
        price: str,
        quantity: str,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """
        下限价订单
        """
        data = {
            "baseAsset": base_asset,
            "quoteAsset": quote_asset,
            "side": side,
            "type": "LIMIT",
            "price": price,
            "quantity": quantity,
            "timeInForce": time_in_force,
        }
        client = HTTPClientFactory.get_client()
        resp = await client.post(LimitOrderAPI.PLACE_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    @staticmethod
    async def cancel_order(
        headers: dict[str, str], order_id: str, base_asset: str, quote_asset: str
    ) -> dict[str, Any]:
        """
        撤销指定订单
        """
        data = {"orderId": order_id, "baseAsset": base_asset, "quoteAsset": quote_asset}
        client = HTTPClientFactory.get_client()
        resp = await client.post(LimitOrderAPI.CANCEL_URL, headers=headers, json=data)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
