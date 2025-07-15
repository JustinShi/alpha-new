"""
价格监控与订单推送监控模块
严格使用API_REFERENCE_MERGED.md文档中的ws地址和订阅格式。
集成listenKey实时获取、自动重连、推送日志等功能。
"""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from src.alpha_new.models.ws_w3w_model import LISTEN_KEY_URL, ORDER_WS_URL, PRICE_WS_URL

# 日志配置
logger = logging.getLogger("ws_monitor")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("ws_monitor.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


async def monitor_price(
    session: aiohttp.ClientSession,
    headers: dict[str, str] | None,
    stream_param: str,
    on_message: Callable[[Any], None] | None = None,
    reconnect: int = 3,
) -> None:
    """
    价格推送监控，自动重连。
    :param session: aiohttp.ClientSession（已配置代理）
    :param headers: 请求头
    :param stream_param: 订阅参数（如 btcusdt@aggTrade）
    :param on_message: 可选，收到推送时的回调
    :param reconnect: 断线重连次数
    """
    subscribe_msg = {"method": "SUBSCRIBE", "params": [stream_param], "id": 4}
    ws_headers = headers
    for attempt in range(reconnect):
        try:
            async with session.ws_connect(PRICE_WS_URL, headers=ws_headers) as ws:
                await ws.send_str(json.dumps(subscribe_msg))
                logger.info(f"已发送价格订阅: {subscribe_msg}")
                print(f"已发送价格订阅: {subscribe_msg}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        # 跳过订阅确认消息
                        if "id" in data and len(data) == 1:
                            continue
                        if "result" in data and data["result"] is None:
                            continue
                        logger.info(f"[价格推送]{data}")
                        if on_message:
                            (
                                await on_message(data)
                                if asyncio.iscoroutinefunction(on_message)
                                else on_message(data)
                            )
                        else:
                            print("[价格推送]", data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket错误: {msg}")
                        break
        except Exception as e:
            logger.error(f"价格推送连接异常: {e}")
            await asyncio.sleep(3)
            print(f"价格推送重连中...({attempt+1}/{reconnect})")
        else:
            break


async def get_listen_key(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    cookies: dict[str, str] | None,
) -> str | None:
    """
    获取listenKey用于订单推送。
    根据文档，返回格式为: {"listenKey": "string"}
    """
    try:
        print("[调试] 请求headers:", headers)
        print("[调试] 请求cookies:", cookies)
        async with session.post(
            LISTEN_KEY_URL, headers=headers, cookies=cookies, json={}
        ) as resp:
            print("[调试] 响应状态:", resp.status)
            resp_text = await resp.text()
            print("[调试] 响应内容:", resp_text)
            resp.raise_for_status()
            data = json.loads(resp_text)
            # 根据文档，返回格式为 {"listenKey": "string"}
            # 但实际返回可能是 {"data": "string"}，需要兼容两种格式
            listen_key = data.get("listenKey") or data.get("data")
            logger.info(f"获取listenKey: {listen_key}")
            return listen_key
    except Exception as e:
        logger.error(f"获取listenKey失败: {e}")
        print("获取listenKey失败:", e)
        return None


async def monitor_order(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    listen_key: str,
    on_message: Callable[[Any], None] | None = None,
    reconnect: int = 3,
) -> None:
    """
    订单推送监控（只用外部传入的listenKey，不自动获取/刷新）
    """
    subscribe_msg = {
        "method": "SUBSCRIBE",
        "params": [f"alpha@{listen_key}"],  # 修正为文档格式
        "id": 3,
    }
    ws_headers = headers
    for attempt in range(reconnect):
        try:
            async with session.ws_connect(ORDER_WS_URL, headers=ws_headers) as ws:
                await ws.send_str(json.dumps(subscribe_msg))
                logger.info(f"已发送订单订阅: {subscribe_msg}")
                print(f"已发送订单订阅: {subscribe_msg}")
                async for msg in ws:
                    print("[订单推送原始消息]", msg.data)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            # 跳过订阅确认消息
                            if "id" in data and len(data) == 1:
                                continue
                            if "result" in data and data["result"] is None:
                                print("[订单推送订阅确认]", data)
                                continue
                            print("[订单推送解析后]", data)
                        except Exception as e:
                            print("[订单推送解析异常]", e)
                            data = msg.data
                        logger.info(f"[订单推送]{data}")
                        if on_message:
                            (
                                await on_message(data)
                                if asyncio.iscoroutinefunction(on_message)
                                else on_message(data)
                            )
                        else:
                            print("[订单推送]", data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket错误: {msg}")
                        break
        except Exception as e:
            logger.error(f"订单推送连接异常: {e}")
            await asyncio.sleep(3)
            print(f"订单推送重连中...({attempt+1}/{reconnect})")
        else:
            break
