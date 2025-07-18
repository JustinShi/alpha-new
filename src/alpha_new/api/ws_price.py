from collections.abc import Awaitable, Callable
from typing import Any

from .ws_client import AlphaWebSocketClient


class PriceWebSocket(AlphaWebSocketClient):
    def __init__(
        self,
        on_price: Callable[[dict[str, Any]], Awaitable[None]],
        chain_addr: str,
        chain_id: str,
        interval: str = "kline_1s",
        **kwargs: Any,
    ) -> None:
        url = "wss://nbstream.binance.com/w3w/wsa/stream"
        super().__init__(url, **kwargs)
        self._chain_addr = chain_addr
        self._chain_id = chain_id
        self._interval = interval
        self.on_message(self._handle_message)
        self._on_price = on_price
        self._subscribed = False

    async def subscribe_price(self) -> None:
        param = f"came@{self._chain_addr}@{self._chain_id}@{self._interval}"
        await self.send({"method": "SUBSCRIBE", "params": [param], "id": 4})
        self._subscribed = True

    async def unsubscribe_price(self) -> None:
        param = f"came@{self._chain_addr}@{self._chain_id}@{self._interval}"
        await self.send({"method": "UNSUBSCRIBE", "params": [param], "id": 4})
        self._subscribed = False

    async def _handle_message(self, data: dict[str, Any]) -> None:
        # 只处理价格推送消息
        if data.get("data", {}).get("e") == "kline":
            await self._on_price(data["data"])
