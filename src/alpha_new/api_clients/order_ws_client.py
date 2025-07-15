"""
订单推送WebSocket客户端
继承自BaseWebSocketClient，专门处理订单推送
包含listenKey自动刷新机制
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from src.alpha_new.api_clients.base_ws_client import BaseWebSocketClient
from src.alpha_new.models.ws_w3w_model import (
    LISTEN_KEY_URL,
    ORDER_WS_URL,
    OrderPushModel,
)


class OrderWebSocketClient(BaseWebSocketClient):
    """订单推送WebSocket客户端"""

    def __init__(
        self,
        headers: dict[str, str],
        cookies: dict[str, str] | None = None,
        listen_key_refresh_interval: int = 1800,  # 30分钟刷新一次
        **kwargs,
    ) -> None:
        super().__init__(
            ws_url=ORDER_WS_URL, headers=headers, logger_name="order_ws", **kwargs
        )
        self.cookies = cookies
        self._listen_key: str | None = None
        self._listen_key_refresh_interval = listen_key_refresh_interval
        self._listen_key_refresh_task: asyncio.Task | None = None
        self._last_listen_key_refresh = datetime.now()

    async def _create_subscription_message(self, params: Any) -> dict:
        """创建订单订阅消息"""
        if isinstance(params, str):
            # 如果是listenKey，添加alpha@前缀
            if not params.startswith("alpha@"):
                params = f"alpha@{params}"
            params = [params]

        return {"method": "SUBSCRIBE", "params": params, "id": 3}

    async def _process_message(self, message: dict) -> dict | None:
        """处理订单推送消息"""
        # 跳过订阅确认消息
        if "id" in message and ("result" in message or len(message) == 1):
            self.logger.debug(f"订阅确认: {message}")
            return None

        # 处理订单数据
        if "stream" in message and "data" in message:
            try:
                # 直接返回原始消息，让回调处理解析
                return message
            except Exception as e:
                self.logger.error(f"处理订单数据失败: {e}, 原始数据: {message}")
                return None

        return None

    async def get_listen_key(self) -> str | None:
        """获取listenKey"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.post(
                LISTEN_KEY_URL, headers=self.headers, cookies=self.cookies, json={}
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                # 兼容两种返回格式
                listen_key = data.get("listenKey") or data.get("data")
                if listen_key:
                    self._listen_key = listen_key
                    self._last_listen_key_refresh = datetime.now()
                    self.logger.info(f"获取listenKey成功: {listen_key[:10]}...")
                    return listen_key
                self.logger.error(f"获取listenKey失败，响应数据: {data}")
                return None

        except Exception as e:
            self.logger.error(f"获取listenKey异常: {e}")
            return None

    async def refresh_listen_key(self) -> bool:
        """刷新listenKey（延长有效期）"""
        if not self._listen_key:
            self.logger.warning("没有listenKey可刷新")
            return False

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # 使用PUT请求延长listenKey有效期
            async with self.session.put(
                LISTEN_KEY_URL,
                headers=self.headers,
                cookies=self.cookies,
                json={"listenKey": self._listen_key},
            ) as resp:
                if resp.status == 200:
                    self._last_listen_key_refresh = datetime.now()
                    self.logger.info("刷新listenKey成功")
                    return True
                self.logger.error(f"刷新listenKey失败: {resp.status}")
                return False

        except Exception as e:
            self.logger.error(f"刷新listenKey异常: {e}")
            return False

    async def _listen_key_refresh_loop(self) -> None:
        """listenKey自动刷新循环"""
        while self._running and self._listen_key:
            try:
                # 计算下次刷新时间
                next_refresh = self._last_listen_key_refresh + timedelta(
                    seconds=self._listen_key_refresh_interval
                )
                sleep_time = (next_refresh - datetime.now()).total_seconds()

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

                # 刷新listenKey
                if not await self.refresh_listen_key():
                    # 刷新失败，尝试重新获取
                    self.logger.warning("listenKey刷新失败，尝试重新获取")
                    new_key = await self.get_listen_key()
                    if new_key:
                        # 重新订阅
                        await self.subscribe(new_key)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"listenKey刷新循环异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试

    async def connect_and_subscribe(self, listen_key: str | None = None) -> bool:
        """连接并订阅

        Args:
            listen_key: 可选的listenKey，如果不提供则自动获取
        """
        # 获取或使用提供的listenKey
        if not listen_key:
            listen_key = await self.get_listen_key()
            if not listen_key:
                self.logger.error("无法获取listenKey")
                return False
        else:
            self._listen_key = listen_key

        # 连接WebSocket
        if not await self.connect():
            return False

        # 订阅
        if not await self.subscribe(listen_key):
            await self.disconnect()
            return False

        # 启动listenKey刷新任务
        self._listen_key_refresh_task = asyncio.create_task(
            self._listen_key_refresh_loop()
        )

        return True

    async def disconnect(self) -> None:
        """断开连接"""
        # 取消listenKey刷新任务
        if self._listen_key_refresh_task:
            self._listen_key_refresh_task.cancel()

        await super().disconnect()

    def get_stats(self) -> dict:
        """获取统计信息（包含listenKey信息）"""
        stats = super().get_stats()
        stats["listen_key"] = (
            self._listen_key[:10] + "..." if self._listen_key else None
        )
        stats["last_listen_key_refresh"] = str(self._last_listen_key_refresh)
        return stats


# 使用示例
async def order_monitor_example() -> None:
    """订单监控示例"""

    # 消息处理回调
    async def on_order_message(data: dict) -> None:
        # 解析为Pydantic模型
        order_model = OrderPushModel(**data)
        order = order_model.data
        print(
            f"[订单] {order.s} {order.S} {order.X}: "
            f"价格={order.p}, 数量={order.q}, "
            f"订单ID={order.i}"
        )

    # 创建客户端
    headers = {
        "User-Agent": "Mozilla/5.0",
        # 添加其他必要的headers
    }
    cookies = {
        # 添加必要的cookies
    }

    client = OrderWebSocketClient(
        headers=headers,
        cookies=cookies,
        heartbeat_interval=30,
        listen_key_refresh_interval=1800,  # 30分钟
    )

    # 设置回调
    client.set_callbacks(
        on_message=on_order_message,
        on_connect=lambda: print("订单WebSocket已连接"),
        on_disconnect=lambda: print("订单WebSocket已断开"),
        on_error=lambda e: print(f"订单WebSocket错误: {e}"),
    )

    # 连接并订阅
    if await client.connect_and_subscribe():
        print("订单监控已启动，等待订单推送...")

        # 运行60秒
        await asyncio.sleep(60)

        # 获取统计信息
        stats = client.get_stats()
        print(f"统计信息: {stats}")

        # 断开连接
        await client.disconnect()
    else:
        print("订单监控启动失败")


if __name__ == "__main__":
    asyncio.run(order_monitor_example())
