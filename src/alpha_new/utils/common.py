"""
通用工具函数模块
消除代码库中的重复函数
"""

import json
from pathlib import Path
from typing import Any


def decode_dict(d: dict[Any, Any] | None) -> dict[str, str]:
    """
    将字典的key/value从bytes转换为str

    这个函数在多个脚本中重复定义，现在统一到这里

    Args:
        d: 输入字典，可能包含bytes类型的key或value

    Returns:
        转换后的字典，所有key和value都是str类型
    """
    if not d:
        return {}

    result = {}
    for k, v in d.items():
        # 转换key
        if isinstance(k, bytes):
            key = k.decode("utf-8")
        else:
            key = str(k)

        # 转换value
        if isinstance(v, bytes):
            value = v.decode("utf-8")
        else:
            value = str(v) if v is not None else ""

        result[key] = value

    return result


def load_json_file(file_path: str | Path, default: Any = None) -> Any:
    """
    安全加载JSON文件

    Args:
        file_path: JSON文件路径
        default: 文件不存在或加载失败时的默认值

    Returns:
        JSON数据或默认值
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return default

        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(data: Any, file_path: str | Path, ensure_dir: bool = True) -> bool:
    """
    安全保存JSON文件

    Args:
        data: 要保存的数据
        file_path: 保存路径
        ensure_dir: 是否确保目录存在

    Returns:
        是否保存成功
    """
    try:
        path = Path(file_path)

        if ensure_dir:
            path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception:
        return False


def ensure_directory(dir_path: str | Path) -> Path:
    """
    确保目录存在

    Args:
        dir_path: 目录路径

    Returns:
        Path对象
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数

    Args:
        value: 要转换的值
        default: 转换失败时的默认值

    Returns:
        整数值
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全转换为浮点数

    Args:
        value: 要转换的值
        default: 转换失败时的默认值

    Returns:
        浮点数值
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化的文件大小字符串
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截断字符串

    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后的后缀

    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """
    合并多个字典

    Args:
        *dicts: 要合并的字典

    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def get_nested_value(
    data: dict[str, Any], key_path: str, default: Any = None, separator: str = "."
) -> Any:
    """
    获取嵌套字典中的值

    Args:
        data: 字典数据
        key_path: 键路径，如 "user.profile.name"
        default: 默认值
        separator: 分隔符

    Returns:
        值或默认值
    """
    try:
        keys = key_path.split(separator)
        value = data

        for key in keys:
            value = value[key]

        return value
    except (KeyError, TypeError):
        return default


def set_nested_value(
    data: dict[str, Any], key_path: str, value: Any, separator: str = "."
) -> None:
    """
    设置嵌套字典中的值

    Args:
        data: 字典数据
        key_path: 键路径，如 "user.profile.name"
        value: 要设置的值
        separator: 分隔符
    """
    keys = key_path.split(separator)
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value


# 向后兼容的别名
decode_user_data = decode_dict  # 为了向后兼容
