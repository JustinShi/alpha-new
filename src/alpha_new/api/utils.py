import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class APIError(Exception):
    """统一API异常基类"""


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]
]:
    """
    异步自动重试装饰器
    :param max_retries: 最大重试次数
    :param delay: 每次重试间隔(秒)
    :param exceptions: 需要重试的异常类型
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
            raise APIError(
                f"API调用重试{max_retries}次仍失败: {last_exc}"
            ) from last_exc

        return wrapper

    return decorator
