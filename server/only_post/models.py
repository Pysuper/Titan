"""
@Project ：Titan
@File    ：models.py
@Author  ：PySuper
@Date    ：2025/4/29 10:53
@Desc    ：数据模型定义
"""

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# 定义请求数据模型
class PostData(BaseModel):
    message: str = Field(..., description="消息内容")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


# 定义算法结果模型
class ResultData(BaseModel):
    status: str = Field()
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# 定义响应数据模型
class ResponseData(BaseModel):
    status: str = Field()
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
