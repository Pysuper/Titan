"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：请求处理中间件
"""

import json
import time
import hashlib
import random
import asyncio
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

from logic.config import get_logger

logger = get_logger("middleware")


def add_cors_middleware(app: FastAPI) -> None:
    """添加跨域中间件到FastAPI应用"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.debug("已添加跨域中间件")


class RequestParserMiddleware(BaseHTTPMiddleware):
    """请求参数解析中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    json_body = json.loads(body)
                    request.state.json_body = json_body
                    logger.debug(f"解析JSON请求体: {json_body}")
            except json.JSONDecodeError:
                logger.warning("无法解析请求体为JSON")
                request.state.json_body = {}

        query_params = dict(request.query_params)
        request.state.query_params = query_params
        request.state.all_params = {**getattr(request.state, "json_body", {}), **query_params}
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志记录中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = hashlib.md5(f"{time.time()}-{random.random()}".encode()).hexdigest()[:8]
        request.state.request_id = request_id

        start_time = time.time()
        logger.info(f"[{request_id}] 开始处理 {request.method} {request.url.path} 请求")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"[{request_id}] 完成处理 {request.method} {request.url.path} 请求，状态码: {response.status_code}，耗时: {process_time:.4f}秒"
        )

        response.headers["X-Request-ID"] = request_id
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    """超时中间件"""

    def __init__(self, app, timeout: float = 10.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"请求处理超时 (>{self.timeout}秒)")
            return JSONResponse(status_code=504, content={"status": "error", "message": "请求处理超时", "data": None})
