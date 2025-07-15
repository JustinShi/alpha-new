"""
用户数据结构
用于承载用户相关接口返回的数据。
"""

from pydantic import BaseModel


class UserBaseDetailModel(BaseModel):
    first_name: str | None = None  # 姓名
    email: str | None = None  # 邮箱
    success: bool = False  # 是否成功
