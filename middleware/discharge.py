"""
@Project ：Titan
@File    ：discharge.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：流量处理中间件
"""

import gzip
import zlib
from typing import Callable, Dict

import requests
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logic.config import get_logger

logger = get_logger("middleware")


class TrafficControlMiddleware(BaseHTTPMiddleware):
    """流量控制中间件"""

    def __init__(self, app, max_body_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            logger.warning(f"请求体过大: {content_length} 字节，超过限制: {self.max_body_size} 字节")
            return JSONResponse(
                status_code=413,
                content={
                    "status": "error",
                    "message": f"请求体过大，最大允许 {self.max_body_size} 字节",
                    "data": None,
                },
            )
        return await call_next(request)


class CompressionMiddleware(BaseHTTPMiddleware):
    """压缩中间件"""

    def __init__(self, app, min_size: int = 1024, compression_level: int = 6):
        super().__init__(app)
        self.min_size = min_size
        self.compression_level = compression_level

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if response.headers.get("content-encoding") is None and response.headers.get("content-type", "").startswith(
            ("text/", "application/json", "application/xml")
        ):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            if len(body) >= self.min_size:
                accept_encoding = request.headers.get("accept-encoding", "")
                if "gzip" in accept_encoding.lower():
                    compressed_body = gzip.compress(body, self.compression_level)

                    if len(compressed_body) < len(body):
                        logger.debug(
                            f"压缩响应: {len(body)} -> {len(compressed_body)} 字节，压缩率: {(1 - len(compressed_body) / len(body)) * 100:.2f}%"
                        )

                        headers = dict(response.headers)
                        headers["content-encoding"] = "gzip"
                        headers["content-length"] = str(len(compressed_body))

                        return Response(
                            content=compressed_body,
                            status_code=response.status_code,
                            headers=headers,
                            media_type=response.media_type,
                        )

            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response


class DecompressionMiddleware(BaseHTTPMiddleware):
    """解压缩中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_encoding = request.headers.get("content-encoding", "").lower()

        if content_encoding in ["gzip", "deflate"]:
            body = await request.body()

            try:
                if content_encoding == "gzip":
                    decompressed_body = gzip.decompress(body)
                elif content_encoding == "deflate":
                    decompressed_body = zlib.decompress(body)

                request._body = decompressed_body
                request.headers = {k: v for k, v in request.headers.items() if k.lower() != "content-encoding"}
                request.headers["content-length"] = str(len(decompressed_body))

                logger.debug(f"解压缩请求: {len(body)} -> {len(decompressed_body)} 字节")
            except Exception as e:
                logger.error(f"解压缩请求失败: {str(e)}")
                return JSONResponse(
                    status_code=400, content={"status": "error", "message": f"解压缩请求失败: {str(e)}", "data": None}
                )

        return await call_next(request)


class LoadBalancerMiddleware(BaseHTTPMiddleware):
    """负载均衡中间件"""

    def __init__(self, app, backends: list = None, strategy: str = "round_robin"):
        super().__init__(app)
        self.backends = backends or []
        self.strategy = strategy
        self.current_backend_index = 0
        logger.info(f"负载均衡中间件已初始化，后端服务器: {self.backends}, 策略: {self.strategy}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.backends:
            return await call_next(request)

        if self.strategy == "round_robin":
            backend = self.backends[self.current_backend_index]
            self.current_backend_index = (self.current_backend_index + 1) % len(self.backends)
        else:  # random
            import random

            backend = random.choice(self.backends)

        try:
            url = f"{backend}{request.url.path}"
            if request.url.query:
                url += f"?{request.url.query}"

            body = await request.body()
            response = requests.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                data=body,
                timeout=30,
                allow_redirects=False,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type"),
            )
        except Exception as e:
            logger.error(f"转发请求到 {backend} 失败: {str(e)}")
            if len(self.backends) > 1:
                self.backends.remove(backend)
                logger.warning(f"移除不可用的后端 {backend}，剩余后端: {self.backends}")
                return await self.dispatch(request, call_next)

            return JSONResponse(status_code=503, content={"status": "error", "message": "服务暂时不可用", "data": None})


class RedirectionMiddleware(BaseHTTPMiddleware):
    """重定向中间件"""

    def __init__(self, app, redirect_rules: Dict[str, str] = None):
        super().__init__(app)
        self.redirect_rules = redirect_rules or {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        for prefix, target in self.redirect_rules.items():
            if path.startswith(prefix):
                redirect_url = f"{target}{path[len(prefix):]}"
                if request.url.query:
                    redirect_url += f"?{request.url.query}"

                logger.info(f"重定向请求: {path} -> {redirect_url}")
                return Response(status_code=307, headers={"location": redirect_url})

        return await call_next(request)
