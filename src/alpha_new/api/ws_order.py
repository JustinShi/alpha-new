import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

from .http_client import HTTPClientFactory
from .ws_client import AlphaWebSocketClient


class OrderWebSocket(AlphaWebSocketClient):
    def __init__(
        self,
        on_order: Callable[[dict[str, Any]], Awaitable[None]],
        listen_key: str,
        headers: dict[str, str] | None = None,
        auto_renew: bool = True,
        renew_interval: int = 30 * 60,  # 30分钟
        **kwargs: Any,
    ) -> None:
        url = "wss://nbstream.binance.com/w3w/stream"
        super().__init__(url, headers=headers, **kwargs)
        self._listen_key = listen_key
        self._headers = headers
        self.on_message(self._handle_message)
        self._on_order = on_order
        self._subscribed = False
        self._auto_renew = auto_renew
        self._renew_interval = renew_interval
        self._renew_task: asyncio.Task[None] | None = None
        self._reconnect_lock = asyncio.Lock()

    async def connect(self) -> None:
        await super().connect()
        if self._auto_renew and not self._renew_task:
            self._renew_task = asyncio.create_task(self._renew_listen_key_loop())

    async def subscribe_order(self) -> None:
        param = f"alpha@{self._listen_key}"
        await self.send({"method": "SUBSCRIBE", "params": [param], "id": 3})
        self._subscribed = True

    async def unsubscribe_order(self) -> None:
        param = f"alpha@{self._listen_key}"
        await self.send({"method": "UNSUBSCRIBE", "params": [param], "id": 3})
        self._subscribed = False

    async def _handle_message(self, data: dict[str, Any]) -> None:
        if data.get("data", {}).get("e") == "executionReport":
            await self._on_order(data["data"])

    @staticmethod
    async def get_listen_key(headers: dict[str, str]) -> str | None:
        url = "https://www.binance.com/bapi/defi/v1/private/alpha-trade/get-listen-key"
        client = HTTPClientFactory.get_client()
        resp = await client.post(url, headers=headers, json={})
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], str):
                return data["data"]
            if "listenKey" in data and isinstance(data["listenKey"], str):
                return data["listenKey"]
        return None

    async def _renew_listen_key_loop(self) -> None:
        while self._auto_renew:
            await asyncio.sleep(self._renew_interval)
            with contextlib.suppress(Exception):
                await self._renew_listen_key()

    async def _renew_listen_key(self) -> None:
        # 币安API listenKey续期接口
        url = "https://www.binance.com/bapi/defi/v1/private/alpha-trade/keep-listen-key"
        client = HTTPClientFactory.get_client()
        await client.post(
            url, headers=self._headers, json={"listenKey": self._listen_key}
        )

    async def _reconnect(self) -> None:
        async with self._reconnect_lock:
            # 断线时自动重新获取listenKey
            if self._headers:
                new_key = await self.get_listen_key(self._headers)
                if new_key:
                    self._listen_key = new_key
            await super()._reconnect()
            if self._subscribed:
                await self.subscribe_order()
