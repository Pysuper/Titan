"""
@Project ：Titan
@File    ：model.py
@Author  ：PySuper
@Date    ：2025/4/29 10:41
@Desc    ：Titan model.py
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class DataItem(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
