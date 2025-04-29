"""
@Project ：Titan
@File    ：util.py
@Author  ：PySuper
@Date    ：2025/4/29 10:53
@Desc    ：工具函数
"""

from fastapi import Request
from fastapi.responses import JSONResponse


# 全局异常处理
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "data": None,
        },
    )
