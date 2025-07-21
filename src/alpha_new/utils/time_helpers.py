"""
统一时间处理模块
消除重复的时间处理函数
"""

import asyncio
from datetime import datetime, timedelta

import httpx

from .exceptions import NetworkError
from .exceptions import TimeoutError as AlphaTimeoutError
from .http_pool import get_binance_api_client, get_time_api_client

# 常用的时间API端点
BINANCE_TIME_API = "https://api.binance.com/api/v3/time"
WORLDTIME_API = "http://worldtimeapi.org/api/timezone/Etc/UTC"


async def get_binance_server_time() -> datetime:
    """
    获取币安服务器时间（优化版本 - 使用连接池）

    Returns:
        币安服务器时间

    Raises:
        NetworkError: 网络请求失败
        AlphaTimeoutError: 请求超时
    """
    try:
        # 🚀 优化：使用全局连接池
        client = await get_binance_api_client()
        response = await client.get(BINANCE_TIME_API)
        response.raise_for_status()

        data = response.json()
        server_time_ms = data["serverTime"]

        return datetime.fromtimestamp(server_time_ms / 1000)

    except httpx.TimeoutException:
        raise AlphaTimeoutError("获取币安服务器时间超时")
    except httpx.RequestError as e:
        raise NetworkError(f"获取币安服务器时间失败: {e}")
    except Exception as e:
        raise NetworkError(f"解析币安服务器时间失败: {e}")


async def get_utc_time() -> datetime:
    """
    获取UTC时间（通过API）（优化版本 - 使用连接池）

    Returns:
        UTC时间

    Raises:
        NetworkError: 网络请求失败
        AlphaTimeoutError: 请求超时
    """
    try:
        # 🚀 优化：使用全局连接池
        client = await get_time_api_client()
        response = await client.get(WORLDTIME_API)
        response.raise_for_status()

        data = response.json()
        utc_time_str = data["utc_datetime"]

        # 解析ISO格式时间
        return datetime.fromisoformat(utc_time_str.replace("Z", "+00:00")).replace(
            tzinfo=None
        )

    except httpx.TimeoutException:
        raise AlphaTimeoutError("获取UTC时间超时")
    except httpx.RequestError as e:
        raise NetworkError(f"获取UTC时间失败: {e}")
    except Exception as e:
        raise NetworkError(f"解析UTC时间失败: {e}")


async def calibrate_time_offset(server_time_func=None, samples: int = 3) -> float:
    """
    校准本地时间与服务器时间的偏移

    Args:
        server_time_func: 获取服务器时间的函数，默认使用币安API
        samples: 采样次数，用于计算平均偏移

    Returns:
        时间偏移（秒），本地时间 + 偏移 ≈ 服务器时间

    Raises:
        NetworkError: 网络请求失败
    """
    if server_time_func is None:
        server_time_func = get_binance_server_time

    offsets = []

    for _ in range(samples):
        try:
            local_before = datetime.now()
            server_time = await server_time_func()
            local_after = datetime.now()

            # 使用请求中点时间计算偏移
            local_mid = local_before + (local_after - local_before) / 2
            offset = (server_time - local_mid).total_seconds()

            offsets.append(offset)

            # 避免请求过于频繁
            if _ < samples - 1:
                await asyncio.sleep(0.1)

        except Exception:
            # 忽略单次失败，继续尝试
            continue

    if not offsets:
        raise NetworkError("无法获取服务器时间进行校准")

    # 返回平均偏移
    return sum(offsets) / len(offsets)


def get_next_target_time(
    hour: int, minute: int = 0, second: int = 0, base_time: datetime | None = None
) -> datetime:
    """
    获取下一个目标时间

    Args:
        hour: 目标小时
        minute: 目标分钟
        second: 目标秒
        base_time: 基准时间，默认为当前时间

    Returns:
        下一个目标时间
    """
    if base_time is None:
        base_time = datetime.now()

    target = base_time.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # 如果目标时间已过，则设为明天
    if target <= base_time:
        target += timedelta(days=1)

    return target


def get_previous_target_time(
    hour: int, minute: int = 0, second: int = 0, base_time: datetime | None = None
) -> datetime:
    """
    获取上一个目标时间

    Args:
        hour: 目标小时
        minute: 目标分钟
        second: 目标秒
        base_time: 基准时间，默认为当前时间

    Returns:
        上一个目标时间
    """
    if base_time is None:
        base_time = datetime.now()

    target = base_time.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # 如果目标时间未到，则设为昨天
    if target > base_time:
        target -= timedelta(days=1)

    return target


def calculate_sleep_time(
    target_time: datetime, advance_ms: int = 0, current_time: datetime | None = None
) -> float:
    """
    计算到目标时间的睡眠时间

    Args:
        target_time: 目标时间
        advance_ms: 提前毫秒数
        current_time: 当前时间，默认为系统时间

    Returns:
        睡眠时间（秒），如果为负数表示已过期
    """
    if current_time is None:
        current_time = datetime.now()

    # 计算到目标时间的秒数
    time_diff = (target_time - current_time).total_seconds()

    # 减去提前时间
    sleep_time = time_diff - (advance_ms / 1000)

    return sleep_time


async def wait_until_time(
    target_time: datetime, advance_ms: int = 0, check_interval: float = 0.1
) -> None:
    """
    等待到指定时间

    Args:
        target_time: 目标时间
        advance_ms: 提前毫秒数
        check_interval: 检查间隔（秒）
    """
    while True:
        sleep_time = calculate_sleep_time(target_time, advance_ms)

        if sleep_time <= 0:
            break

        if sleep_time > check_interval:
            await asyncio.sleep(check_interval)
        else:
            await asyncio.sleep(sleep_time)
            break


def format_duration(seconds: float) -> str:
    """
    格式化时间间隔

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    if seconds < 0:
        return "已过期"

    if seconds < 60:
        return f"{seconds:.1f}秒"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}小时{minutes}分"


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        dt: 时间对象
        format_str: 格式字符串

    Returns:
        格式化的时间字符串
    """
    return dt.strftime(format_str)


def parse_time_string(time_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析时间字符串

    Args:
        time_str: 时间字符串
        format_str: 格式字符串

    Returns:
        时间对象

    Raises:
        ValueError: 解析失败
    """
    return datetime.strptime(time_str, format_str)


# 向后兼容的别名
get_binance_time = get_binance_server_time
