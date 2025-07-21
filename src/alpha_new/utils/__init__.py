"""
工具模块
"""

from .common import (
    decode_dict,
    ensure_directory,
    format_file_size,
    get_nested_value,
    load_json_file,
    merge_dicts,
    safe_float,
    safe_int,
    save_json_file,
    set_nested_value,
    truncate_string,
)
from .database import (
    close_database,
    database_context,
    get_db_engine,
    get_db_session,
    init_database,
    # 向后兼容
    init_db,
    with_database,
)
from .logger import (
    get_api_logger,
    get_claim_logger,
    get_cli_logger,
    get_db_logger,
    get_logger,
    get_order_data_logger,
    get_script_logger,
)
from .time_helpers import (
    calculate_sleep_time,
    calibrate_time_offset,
    format_duration,
    format_timestamp,
    get_binance_server_time,
    # 向后兼容
    get_binance_time,
    get_next_target_time,
    get_previous_target_time,
    get_utc_time,
    wait_until_time,
)

__all__ = [
    # 日志相关
    "get_logger",
    "get_api_logger",
    "get_db_logger",
    "get_script_logger",
    "get_cli_logger",
    "get_claim_logger",
    "get_order_data_logger",
    # 通用工具
    "decode_dict",
    "load_json_file",
    "save_json_file",
    "ensure_directory",
    "safe_int",
    "safe_float",
    "format_file_size",
    "truncate_string",
    "merge_dicts",
    "get_nested_value",
    "set_nested_value",
    # 数据库相关
    "init_database",
    "get_db_session",
    "get_db_engine",
    "close_database",
    "database_context",
    "with_database",
    "init_db",  # 向后兼容
    # 时间相关
    "get_binance_server_time",
    "get_utc_time",
    "calibrate_time_offset",
    "get_next_target_time",
    "get_previous_target_time",
    "calculate_sleep_time",
    "wait_until_time",
    "format_duration",
    "format_timestamp",
    "get_binance_time",  # 向后兼容
]
