"""
@Project ：Titan
@File    ：discharge.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：流量处理中间件
"""

import gzip
import time
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
    """解压缩中间件

    支持多种压缩格式的自动解压缩，包括gzip、deflate、br(Brotli)等
    可配置最大解压缩大小限制，防止解压炸弹攻击
    """

    def __init__(
        self,
        app,
        max_decompression_size: int = 100 * 1024 * 1024,  # 默认最大解压100MB
        supported_encodings: list = None,
    ):
        super().__init__(app)
        self.max_decompression_size = max_decompression_size
        self.supported_encodings = supported_encodings or ["gzip", "deflate", "br"]
        logger.debug(
            f"解压缩中间件已初始化，支持格式: {self.supported_encodings}, 最大解压大小: {self.max_decompression_size/1024/1024:.1f}MB"
        )

        # 检查可选依赖
        self._has_brotli = False
        try:
            import brotli

            self._has_brotli = True
        except ImportError:
            if "br" in self.supported_encodings:
                logger.warning("Brotli库未安装，无法支持br格式解压缩。可通过 pip install brotli 安装")
                self.supported_encodings.remove("br")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_encoding = request.headers.get("content-encoding", "").lower()

        # 检查是否需要解压缩
        if content_encoding and any(enc in content_encoding for enc in self.supported_encodings):
            # 提取实际使用的编码方式（可能有多个，如gzip, deflate）
            encodings = [enc for enc in self.supported_encodings if enc in content_encoding]

            if not encodings:
                logger.warning(f"不支持的压缩格式: {content_encoding}")
                return await call_next(request)

            body = await request.body()
            original_size = len(body)

            if original_size == 0:
                logger.debug("请求体为空，跳过解压缩")
                return await call_next(request)

            try:
                # 按照编码顺序依次解压
                decompressed_body = body
                for encoding in reversed(encodings):  # 反向处理，因为压缩通常是按顺序叠加的
                    start_time = time.perf_counter()

                    if encoding == "gzip":
                        decompressed_body = gzip.decompress(decompressed_body)
                    elif encoding == "deflate":
                        # 尝试两种deflate模式，有些客户端不添加zlib头
                        try:
                            decompressed_body = zlib.decompress(decompressed_body)
                        except zlib.error:
                            decompressed_body = zlib.decompress(decompressed_body, -zlib.MAX_WBITS)
                    elif encoding == "br" and self._has_brotli:
                        import brotli

                        decompressed_body = brotli.decompress(decompressed_body)

                    elapsed = time.perf_counter() - start_time
                    current_size = len(decompressed_body)

                    # 检查解压后大小是否超过限制
                    if current_size > self.max_decompression_size:
                        logger.warning(
                            f"解压后大小 {current_size/1024/1024:.2f}MB 超过限制 {self.max_decompression_size/1024/1024:.2f}MB，可能是解压炸弹攻击"
                        )
                        return JSONResponse(
                            status_code=413,
                            content={"status": "error", "message": "解压后数据超过大小限制", "data": None},
                        )

                    compression_ratio = current_size / (len(body) or 1)
                    logger.debug(
                        f"使用 {encoding} 解压缩: {len(body)/1024:.2f}KB -> {current_size/1024:.2f}KB, "
                        f"压缩比: {compression_ratio:.2f}x, 耗时: {elapsed*1000:.2f}ms"
                    )

                # 更新请求对象
                request._body = decompressed_body

                # 创建新的headers字典，移除content-encoding
                headers = dict(request.headers.items())
                headers.pop("content-encoding", None)
                headers["content-length"] = str(len(decompressed_body))

                # 更新请求头
                request._headers = headers

                logger.info(
                    f"请求解压缩完成: {original_size/1024:.2f}KB -> {len(decompressed_body)/1024:.2f}KB, "
                    f"压缩比: {len(decompressed_body)/original_size:.2f}x"
                )

            except Exception as e:
                logger.error(f"解压缩请求失败: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": f"解压缩请求失败: {str(e)}",
                        "data": {"content_encoding": content_encoding, "body_size": len(body)},
                    },
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
