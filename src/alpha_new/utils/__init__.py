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
    "calculate_sleep_time",
    "calibrate_time_offset",
    "close_database",
    "database_context",
    "decode_dict",
    "ensure_directory",
    "format_duration",
    "format_file_size",
    "format_timestamp",
    "get_api_logger",
    "get_binance_server_time",
    "get_binance_time",  # 向后兼容
    "get_claim_logger",
    "get_cli_logger",
    "get_db_engine",
    "get_db_logger",
    "get_db_session",
    "get_logger",
    "get_nested_value",
    "get_next_target_time",
    "get_order_data_logger",
    "get_previous_target_time",
    "get_script_logger",
    "get_utc_time",
    "init_database",
    "init_db",  # 向后兼容
    "load_json_file",
    "merge_dicts",
    "safe_float",
    "safe_int",
    "save_json_file",
    "set_nested_value",
    "truncate_string",
    "wait_until_time",
    "with_database",
]
