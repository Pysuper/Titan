"""
@Project ：Titan
@File    ：security.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：安全相关中间件
"""

import base64
import hashlib
import json
import time
from typing import Callable, List

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logic.config import get_logger

logger = get_logger("middleware")


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app, allowed_ips: List[str] = None):
        super().__init__(app)
        self.allowed_ips = allowed_ips or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("安全中间件")
        logger.debug(f"【安全中间件】 请求路径: {request.url.path}")
        client_ip = request.client.host if request.client else None
        if self.allowed_ips and client_ip not in self.allowed_ips:
            logger.warning(f"【安全中间件】 拒绝来自 {client_ip} 的未授权访问")
            return JSONResponse(status_code=403, content={"status": "error", "message": "访问被拒绝", "data": None})

        user_agent = request.headers.get("user-agent", "")
        if not user_agent or "bot" in user_agent.lower():
            logger.warning(f"【安全中间件】 可疑的User-Agent: {user_agent}")
            return JSONResponse(status_code=403, content={"status": "error", "message": "访问被拒绝", "data": None})

        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """鉴权中间件"""

    def __init__(self, app, api_keys: List[str] = None, exclude_paths: List[str] = None):
        super().__init__(app)
        self.api_keys = api_keys or []
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if not api_key or (self.api_keys and api_key not in self.api_keys):
            logger.warning(f"未授权访问: {request.url.path}, API密钥: {api_key}")
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": "未授权访问，请提供有效的API密钥",
                    "data": None,
                },
            )

        request.state.api_key = api_key
        return await call_next(request)


class EncryptionMiddleware(BaseHTTPMiddleware):
    """加密中间件"""

    def __init__(self, app, secret_key: str = None):
        super().__init__(app)
        self.secret_key = secret_key or hashlib.sha256(str(time.time()).encode()).hexdigest()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        encrypt_header = request.headers.get("x-encrypt-response", "").lower()
        if encrypt_header == "true" and response.headers.get("content-type") == "application/json":
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                encrypted_body = base64.b64encode(body).decode()
                return JSONResponse(
                    content={"encrypted": True, "data": encrypted_body},
                    status_code=response.status_code,
                    headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
                )
            except Exception as e:
                logger.error(f"加密响应失败: {str(e)}")

        return response


class DecryptionMiddleware(BaseHTTPMiddleware):
    """解密中间件"""

    def __init__(self, app, secret_key: str = None):
        super().__init__(app)
        self.secret_key = secret_key or hashlib.sha256(str(time.time()).encode()).hexdigest()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type and request.headers.get("x-encrypted", "").lower() == "true":
            try:
                body = await request.body()
                body_json = json.loads(body)

                if "data" in body_json and isinstance(body_json["data"], str):
                    decrypted_data = base64.b64decode(body_json["data"])
                    request._body = decrypted_data
                    request.headers = {k: v for k, v in request.headers.items() if k.lower() != "x-encrypted"}
                    request.headers["content-length"] = str(len(decrypted_data))
                    logger.debug("请求数据已解密")
            except Exception as e:
                logger.error(f"解密请求失败: {str(e)}")
                return JSONResponse(
                    status_code=400, content={"status": "error", "message": f"解密请求失败: {str(e)}", "data": None}
                )

        return await call_next(request)
