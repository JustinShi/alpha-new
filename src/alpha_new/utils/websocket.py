import asyncio
import json
import logging

import httpx
import websockets

ORDER_WS_URL = "wss://nbstream.binance.com/w3w/stream"
PRICE_WS_URL = "wss://nbstream.binance.com/w3w/wsa/stream"


class BinanceWebSocket:
    def __init__(self):
        self._running = False
        self._order_ws = None
        self._price_ws = None
        self.order_queue: asyncio.Queue = asyncio.Queue()
        self.price_queue: asyncio.Queue = asyncio.Queue()
        self._listen_key = None
        self._listen_key_task = None
        self._stop_event = asyncio.Event()
        self._logger = logging.getLogger("alpha_new.websocket")
        # 重连配置
        self._max_reconnect_attempts = 5
        self._base_reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._reconnect_attempts = 0
        self._max_retries = 5
        self._retry_interval = 5  # 秒
        self._ping_interval = 20  # 秒

    async def get_listen_key(self, headers: dict, cookies: dict | None = None) -> str:
        """使用移动端认证获取listenKey"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.binance.com/bapi/defi/v1/private/alpha-trade/get-listen-key",
                    headers=headers,
                    cookies=cookies if cookies else {},
                    json={},
                )
                result = response.json()
                if result.get("success"):
                    return result["data"]
                raise Exception(f"获取listenKey失败: {result}")
        except Exception as e:
            raise Exception(f"获取listenKey异常: {e}")

    async def refresh_listen_key(self, headers: dict, cookies: dict | None = None):
        """刷新listenKey（每30分钟）"""
        while self._running:
            try:
                await asyncio.sleep(30 * 60)  # 30分钟
                if self._running:
                    new_key = await self.get_listen_key(headers, cookies)
                    self._listen_key = new_key
                    print(f"listenKey已刷新: {new_key[:20]}...")
            except Exception as e:
                print(f"刷新listenKey失败: {e}")

    async def _ping_loop(self, ws, ws_type):
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._ping_interval)
                await ws.ping()
                self._logger.info(f"[ws][{ws_type}] 发送心跳ping")
            except Exception as e:
                self._logger.warning(f"[ws][{ws_type}] 心跳ping异常: {e}")
                break

    async def _ws_connect_with_retry(
        self, url, ws_type, subscribe_func, *args, **kwargs
    ):
        retry = 0
        while not self._stop_event.is_set():
            try:
                self._logger.info(f"[ws][{ws_type}] 正在连接: {url}")
                async with websockets.connect(url, ping_interval=None) as ws:
                    self._logger.info(f"[ws][{ws_type}] 连接成功")
                    # 启动心跳
                    ping_task = asyncio.create_task(self._ping_loop(ws, ws_type))
                    # 执行订阅
                    await subscribe_func(ws, *args, **kwargs)
                    await ping_task
            except Exception as e:
                self._logger.error(f"[ws][{ws_type}] 连接/订阅异常: {e}")
                retry += 1
                if retry > self._max_retries:
                    self._logger.error(f"[ws][{ws_type}] 重试超限，放弃重连")
                    break
                self._logger.info(
                    f"[ws][{ws_type}] {self._retry_interval}秒后重试第{retry}次..."
                )
                await asyncio.sleep(self._retry_interval)

    async def subscribe_order(self, headers: dict, cookies: dict | None = None):
        """订阅订单推送，自动获取listenKey，支持自动重连"""
        self._running = True
        self._reconnect_attempts = 0

        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self._subscribe_order_internal(headers, cookies)
            except Exception:
                self._reconnect_attempts += 1
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    print(
                        f"订单推送重连失败，已达到最大重试次数: {self._max_reconnect_attempts}"
                    )
                    break

                # 计算重连延迟（指数退避）
                delay = min(
                    self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                    self._max_reconnect_delay,
                )
                print(
                    f"订单推送连接断开，{delay}秒后尝试重连 (第{self._reconnect_attempts}次)..."
                )
                await asyncio.sleep(delay)

        # 清理资源
        if self._listen_key_task:
            self._listen_key_task.cancel()

    async def _subscribe_order_internal(
        self, headers: dict, cookies: dict | None = None
    ):
        """内部订单订阅方法"""
        # 获取初始listenKey
        self._listen_key = await self.get_listen_key(headers, cookies)
        print(f"获取listenKey: {self._listen_key[:20]}...")

        # 启动listenKey刷新任务
        self._listen_key_task = asyncio.create_task(
            self.refresh_listen_key(headers, cookies)
        )

        async def subscribe(ws, headers, cookies):
            sub_msg = json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": [f"alpha@{self._listen_key}"],
                    "id": 3,
                }
            )
            await ws.send(sub_msg)
            listen_key_preview = self._listen_key[:20] if self._listen_key else "None"
            print(f"已订阅订单推送: alpha@{listen_key_preview}...")

            # 重置重连计数
            self._reconnect_attempts = 0

            while self._running:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    await self.order_queue.put(data)
                except websockets.exceptions.ConnectionClosed:
                    print("订单推送连接断开，准备重连...")
                    raise  # 抛出异常触发重连
                except Exception as e:
                    print(f"订单推送异常: {e}")
                    raise  # 抛出异常触发重连

        await self._ws_connect_with_retry(
            ORDER_WS_URL, "order", subscribe, headers, cookies
        )

    async def subscribe_price(self, price_stream: str):
        """订阅价格推送 came@合约@链@kline_1s，支持自动重连"""
        self._running = True
        self._reconnect_attempts = 0

        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self._subscribe_price_internal(price_stream)
            except Exception:
                self._reconnect_attempts += 1
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    print(
                        f"价格推送重连失败，已达到最大重试次数: {self._max_reconnect_attempts}"
                    )
                    break

                # 计算重连延迟（指数退避）
                delay = min(
                    self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                    self._max_reconnect_delay,
                )
                print(
                    f"价格推送连接断开，{delay}秒后尝试重连 (第{self._reconnect_attempts}次)..."
                )
                await asyncio.sleep(delay)

    async def _subscribe_price_internal(self, price_stream: str):
        """内部价格订阅方法"""

        async def subscribe(ws, price_stream):
            sub_msg = json.dumps(
                {"method": "SUBSCRIBE", "params": [price_stream], "id": 4}
            )
            await ws.send(sub_msg)
            print(f"已订阅价格推送: {price_stream}")

            # 重置重连计数
            self._reconnect_attempts = 0

            while self._running:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    await self.price_queue.put(data)
                except websockets.exceptions.ConnectionClosed:
                    print("价格推送连接断开，准备重连...")
                    raise  # 抛出异常触发重连
                except Exception as e:
                    print(f"价格推送异常: {e}")
                    raise  # 抛出异常触发重连

        await self._ws_connect_with_retry(
            PRICE_WS_URL, "price", subscribe, price_stream
        )

    def stop(self):
        """停止所有WebSocket连接"""
        self._running = False
        self._stop_event.set()
        self._logger.info("[ws] 收到停止信号，准备断开所有ws连接")
        if self._listen_key_task:
            self._listen_key_task.cancel()

    @property
    def listen_key(self) -> str | None:
        """获取当前listenKey"""
        return self._listen_key
