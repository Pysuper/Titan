"""
@Project ：Titan
@File    ：cache.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：缓存中间件
"""

import json
from typing import Callable

import redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logic.config import get_logger

logger = get_logger("缓存中间件")


class CacheMiddleware(BaseHTTPMiddleware):
    """缓存中间件"""

    def __init__(self, app, redis_url: str = "redis://localhost:6379/0", ttl: int = 300):
        super().__init__(app)
        self.ttl = ttl
        try:
            self.redis = redis.from_url(redis_url)
            logger.debug(f"已连接到Redis缓存: {redis_url}")
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            self.redis = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # if request.method != "GET" or not self.redis:
        #     return await call_next(request)

        cache_key = f"titan:cache:{request.url.path}:{request.url.query}"

        cached_response = self.redis.get(cache_key)
        if cached_response:
            logger.debug(f"缓存命中: {cache_key}")
            cached_data = json.loads(cached_response)
            return JSONResponse(
                content=cached_data["content"], status_code=cached_data["status_code"], headers=cached_data["headers"]
            )

        response = await call_next(request)

        if response.status_code == 200 and response.headers.get("content-type") == "application/json":
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                response_data = {
                    "content": json.loads(body),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }
                self.redis.setex(cache_key, self.ttl, json.dumps(response_data))
                logger.debug(f"已缓存响应: {cache_key}, TTL: {self.ttl}秒")
            except Exception as e:
                logger.error(f"缓存响应失败: {str(e)}")

            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
