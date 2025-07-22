"""
配置管理模块
提供统一的配置加载和管理功能
"""

import contextlib
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import toml

from .exceptions import ConfigurationError


@dataclass
class DatabaseConfig:
    """数据库配置"""

    url: str = "sqlite+aiosqlite:///data/alpha_users.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class APIConfig:
    """API配置"""

    base_url: str = "https://www.binance.com"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: int = 100  # 每分钟请求数


@dataclass
class LoggingConfig:
    """日志配置"""

    level: str = "INFO"
    file: str | None = "logs/alpha_new.log"
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


@dataclass
class TradingConfig:
    """交易配置"""

    target_token: str = "CROSS"
    buy_amount: float = 10.0
    target_total_amount: float = 40000.0
    buy_slippage: float = 0.005
    sell_slippage: float = 0.005
    max_retry: int = 5
    order_timeout: float = 2.0


@dataclass
class AirdropConfig:
    """空投配置"""

    token_symbol: str = "TA"
    alpha_id: str = ""
    target_hour: int = 15
    target_minute: int = 0
    target_second: int = 0
    advance_ms: int = 1000
    claim_retry_times: int = 15
    query_interval: float = 0.1
    min_score: int = 210


@dataclass
class UserSessionConfig:
    """用户会话配置"""

    check_interval_hours: int = 2
    cache_duration_minutes: int = 30
    min_valid_users: int = 2
    max_concurrent_checks: int = 3
    smart_check_threshold: int = 3


@dataclass
class AppConfig:
    """应用程序配置"""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    airdrop: AirdropConfig = field(default_factory=AirdropConfig)
    user_session: UserSessionConfig = field(default_factory=UserSessionConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """从字典创建配置"""
        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            api=APIConfig(**data.get("api", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            trading=TradingConfig(**data.get("trading", {})),
            airdrop=AirdropConfig(**data.get("airdrop", {})),
            user_session=UserSessionConfig(**data.get("user_session", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "database": self.database.__dict__,
            "api": self.api.__dict__,
            "logging": self.logging.__dict__,
            "trading": self.trading.__dict__,
            "airdrop": self.airdrop.__dict__,
            "user_session": self.user_session.__dict__,
        }


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: AppConfig | None = None
        self._config_file: Path | None = None

    def load_config(self, config_path: str | Path | None = None) -> AppConfig:
        """
        加载配置

        Args:
            config_path: 配置文件路径，如果为None则自动查找

        Returns:
            应用程序配置

        Raises:
            ConfigurationError: 配置加载失败
        """
        config_file = Path(config_path) if config_path else self._find_config_file()

        if config_file and config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = toml.load(f)
                self._config = AppConfig.from_dict(data)
                self._config_file = config_file
            except Exception as e:
                raise ConfigurationError(
                    f"加载配置文件失败: {e}", config_key=str(config_file)
                )
        else:
            # 使用默认配置
            self._config = AppConfig()
            if config_file:
                self._config_file = config_file

        # 应用环境变量覆盖
        self._apply_env_overrides()

        return self._config

    def _find_config_file(self) -> Path | None:
        """查找配置文件"""
        possible_paths = [
            Path("config/app.toml"),
            Path("app.toml"),
            Path("config.toml"),
            Path("alpha_new.toml"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return Path("config/app.toml")  # 默认路径

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        if not self._config:
            return

        # 数据库配置
        if db_url := os.getenv("ALPHA_DATABASE_URL"):
            self._config.database.url = db_url

        # API配置
        if api_timeout := os.getenv("ALPHA_API_TIMEOUT"):
            with contextlib.suppress(ValueError):
                self._config.api.timeout = int(api_timeout)

        # 日志配置
        if log_level := os.getenv("ALPHA_LOG_LEVEL"):
            self._config.logging.level = log_level

        if log_file := os.getenv("ALPHA_LOG_FILE"):
            self._config.logging.file = log_file

    def save_config(self, config_path: str | Path | None = None):
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径，如果为None则使用当前配置文件路径
        """
        if not self._config:
            raise ConfigurationError("没有配置可保存")

        save_path = Path(config_path) if config_path else self._config_file
        if not save_path:
            save_path = Path("config/app.toml")

        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                toml.dump(self._config.to_dict(), f)
        except Exception as e:
            raise ConfigurationError(
                f"保存配置文件失败: {e}", config_key=str(save_path)
            )

    def get_config(self) -> AppConfig:
        """获取当前配置"""
        if not self._config:
            return self.load_config()
        return self._config

    def update_config(self, **kwargs):
        """更新配置"""
        if not self._config:
            self.load_config()

        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ConfigurationError(f"未知的配置项: {key}", config_key=key)


# 全局配置管理器实例
_config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取全局配置"""
    return _config_manager.get_config()


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """加载配置"""
    return _config_manager.load_config(config_path)


def save_config(config_path: str | Path | None = None):
    """保存配置"""
    _config_manager.save_config(config_path)


def update_config(**kwargs):
    """更新配置"""
    _config_manager.update_config(**kwargs)


# 便捷函数
def get_database_url() -> str:
    """获取数据库URL"""
    return get_config().database.url


def get_log_level() -> str:
    """获取日志级别"""
    return get_config().logging.level


def get_api_timeout() -> int:
    """获取API超时时间"""
    return get_config().api.timeout
