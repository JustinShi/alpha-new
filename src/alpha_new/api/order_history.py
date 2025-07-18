"""
订单历史API模块(异步版)
"""

from typing import Any, cast

from .http_client import HTTPClientFactory


class OrderHistoryAPI:
    BASE_URL = "https://www.binance.com/bapi/defi/v1/private/alpha-trade/order/get-order-history-merge"

    @staticmethod
    async def get_order_history(
        headers: dict[str, str],
        base_asset: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        order_status: str | None = None,
        page: int = 1,
        rows: int = 500,
    ) -> dict[str, Any]:
        """
        查询订单历史
        :param headers: 包含认证信息的请求头
        :param base_asset: 币种(可选)
        :param start_time: 开始时间(毫秒时间戳,可选)
        :param end_time: 结束时间(毫秒时间戳,可选)
        :param order_status: 订单状态(可选)
        :param page: 页码
        :param rows: 每页数量
        :return: 订单历史响应
        """
        params = {"page": str(page), "rows": str(rows)}
        if base_asset:
            params["baseAsset"] = base_asset
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        if order_status:
            params["orderStatus"] = order_status
        client = HTTPClientFactory.get_client()
        resp = await client.get(
            OrderHistoryAPI.BASE_URL, headers=headers, params=params
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
