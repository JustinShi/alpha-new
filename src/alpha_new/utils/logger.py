"""
日志工具模块
提供模块级别的日志记录器
"""

import logging
import os


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    获取模块日志记录器

    Args:
        name: 模块名称，如 'alpha_new.api.alpha_api'
        level: 日志级别，可选

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    if level:
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        logger.setLevel(level_map.get(level.upper(), logging.INFO))

    return logger


# 预定义的日志记录器
def get_api_logger() -> logging.Logger:
    """获取API模块日志记录器"""
    return get_logger("alpha_new.api")


def get_db_logger() -> logging.Logger:
    """获取数据库模块日志记录器"""
    return get_logger("alpha_new.db")


def get_script_logger() -> logging.Logger:
    """获取脚本模块日志记录器"""
    return get_logger("alpha_new.scripts")


def get_cli_logger() -> logging.Logger:
    """获取CLI模块日志记录器"""
    return get_logger("alpha_new.cli")


def get_claim_logger() -> logging.Logger:
    """获取领取模块日志记录器"""
    return get_logger("alpha_new.claim")


def get_order_data_logger() -> logging.Logger:
    """获取订单原始数据日志记录器，输出到 logs/order_data.log"""
    logger = get_logger("alpha_new.order_data")
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "order_data.log")
    if not any(
        isinstance(h, logging.FileHandler)
        and h.baseFilename == os.path.abspath(log_path)
        for h in logger.handlers
    ):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
