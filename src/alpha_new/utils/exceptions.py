"""
自定义异常类
为Alpha New项目提供统一的错误处理
"""

from typing import Any


class AlphaBaseError(Exception):
    """Alpha项目基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class AlphaAPIError(AlphaBaseError):
    """API相关错误"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        error_code: str | None = None,
    ):
        self.status_code = status_code
        self.response_data = response_data or {}

        details = {"status_code": status_code, "response_data": response_data}

        super().__init__(message, error_code, details)


class AuthenticationError(AlphaAPIError):
    """认证失败错误"""

    def __init__(self, message: str = "认证失败，请检查登录状态"):
        super().__init__(message, status_code=401, error_code="AUTH_FAILED")


class RateLimitError(AlphaAPIError):
    """请求频率限制错误"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT")


class UserNotFoundError(AlphaBaseError):
    """用户不存在错误"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        message = f"用户{user_id}不存在"
        super().__init__(
            message, error_code="USER_NOT_FOUND", details={"user_id": user_id}
        )


class DatabaseError(AlphaBaseError):
    """数据库操作错误"""

    def __init__(self, message: str, operation: str | None = None):
        self.operation = operation
        details = {"operation": operation} if operation else {}
        super().__init__(message, error_code="DB_ERROR", details=details)


class ConfigurationError(AlphaBaseError):
    """配置错误"""

    def __init__(self, message: str, config_key: str | None = None):
        self.config_key = config_key
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, error_code="CONFIG_ERROR", details=details)


class ValidationError(AlphaBaseError):
    """数据验证错误"""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None
    ):
        self.field = field
        self.value = value
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class NetworkError(AlphaBaseError):
    """网络连接错误"""

    def __init__(self, message: str = "网络连接失败"):
        super().__init__(message, error_code="NETWORK_ERROR")


class TimeoutError(AlphaBaseError):
    """超时错误"""

    def __init__(self, message: str = "操作超时", timeout_seconds: float | None = None):
        self.timeout_seconds = timeout_seconds
        details = {"timeout_seconds": timeout_seconds} if timeout_seconds else {}
        super().__init__(message, error_code="TIMEOUT_ERROR", details=details)


# 便捷函数
def handle_api_error(response, operation: str = "API调用") -> None:
    """
    处理API响应错误

    Args:
        response: HTTP响应对象
        operation: 操作描述

    Raises:
        相应的异常类型
    """
    if response.status_code == 401:
        raise AuthenticationError()
    if response.status_code == 429:
        raise RateLimitError()
    if response.status_code >= 400:
        try:
            error_data = response.json()
            message = error_data.get("message", f"{operation}失败")
        except Exception:
            message = f"{operation}失败 (HTTP {response.status_code})"

        raise AlphaAPIError(
            message=message,
            status_code=response.status_code,
            response_data=error_data if "error_data" in locals() else None,
        )


def validate_user_id(user_id: Any) -> int:
    """
    验证用户ID

    Args:
        user_id: 用户ID（任意类型）

    Returns:
        验证后的用户ID

    Raises:
        ValidationError: 验证失败
    """
    try:
        uid = int(user_id)
        if uid <= 0:
            raise ValidationError("用户ID必须为正整数", field="user_id", value=user_id)
        return uid
    except (ValueError, TypeError):
        raise ValidationError("用户ID格式无效", field="user_id", value=user_id)
