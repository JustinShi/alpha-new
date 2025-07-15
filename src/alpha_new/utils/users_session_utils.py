import json
import logging  # 导入 logging 模块
import sqlite3

logger = logging.getLogger(__name__)  # 获取模块 logger

from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "users_session.db"


def get_headers_cookies(
    username: str, device_type: str = "pc"
) -> tuple[dict, dict | None]:
    """
    根据用户名和端类型获取 headers 和 cookies。
    :param username: 用户名
    :param device_type: 'pc' 或 'mobile'
    :return: (headers, cookies) 或 (headers, None)
    :raises ValueError: headers 或（PC端）cookies 为空时报错
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if device_type == "pc":
            cursor.execute(
                "SELECT headers, cookies FROM user_session_pc WHERE username=?",
                (username,),
            )
            row = cursor.fetchone()
            if row:
                headers = json.loads(row[0])
                cookies = json.loads(row[1])
                if not headers:
                    raise ValueError(f"PC端用户 {username} 的 headers 为空！")
                if not cookies:
                    raise ValueError(f"PC端用户 {username} 的 cookies 为空！")
                return headers, cookies
            raise ValueError(f"PC端未找到用户 {username} 的 session 记录！")
        if device_type == "mobile":
            cursor.execute(
                "SELECT headers FROM user_session_mobile WHERE username=?", (username,)
            )
            row = cursor.fetchone()
            if row:
                headers = json.loads(row[0])
                if not headers:
                    raise ValueError(f"移动端用户 {username} 的 headers 为空！")
                return headers, None
            raise ValueError(f"移动端未找到用户 {username} 的 session 记录！")
        raise ValueError(f"未知的 device_type: {device_type}")
    except Exception as e:
        logger.error(f"读取 user_session_{device_type} 失败: {e}")  # 使用 logger.error
        raise
    finally:
        conn.close()
