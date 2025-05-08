"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/29 13:52
@Desc    ：请求处理中间件
"""

import asyncio
import hashlib
import json
import random
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Dict, Optional, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from decorators.logs import suppress_errors
from logic.config import get_logger


class RequestParserMiddleware(BaseHTTPMiddleware):
    """请求参数解析中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("请求参数解析中间件")
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    json_body = json.loads(body)
                    request.state.json_body = json_body
                    logger.debug(f"【请求参数解析中间件】 解析JSON请求体: {json_body}")
            except json.JSONDecodeError:
                logger.warning("【请求参数解析中间件】 无法解析请求体为JSON")
                request.state.json_body = {}

        query_params = dict(request.query_params)
        request.state.query_params = query_params
        request.state.all_params = {**getattr(request.state, "json_body", {}), **query_params}
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志记录中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("日志记录中间件")
        request_id = hashlib.md5(f"{time.time()}-{random.random()}".encode()).hexdigest()[:8]
        request.state.request_id = request_id

        start_time = time.time()
        logger.debug(f"【日志记录中间件】 [{request_id}] 开始处理 {request.method} {request.url.path} 请求")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.debug(
            f" 【日志记录中间件】 [{request_id}] 完成处理 {request.method} {request.url.path} 请求，状态码: {response.status_code}，耗时: {process_time:.4f}秒"
        )

        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件

    支持多种限流策略：
    1. 全局限流：限制所有请求的总速率
    2. IP限流：针对每个IP地址进行限流
    3. 路径限流：针对特定API路径进行限流
    4. 组合限流：同时应用多种限流策略
    """

    def __init__(
        self,
        app,
        global_rate_limit: int = 100,
        ip_rate_limit: int = 20,
        path_rate_limits: Dict[str, int] = None,
        window_size: float = 1.0,
        block_duration: float = 60.0,
    ):
        """
        初始化限流中间件

        Args:
            app: FastAPI应用
            global_rate_limit: 全局限流阈值（每秒请求数）
            ip_rate_limit: 每个IP的限流阈值（每秒请求数）
            path_rate_limits: 特定路径的限流阈值，格式为{路径前缀: 每秒请求数}
            window_size: 滑动窗口大小（秒）
            block_duration: 触发限流后的封禁时间（秒）
        """

        logger = get_logger("限流中间件")
        super().__init__(app)
        self.global_rate_limit = global_rate_limit
        self.ip_rate_limit = ip_rate_limit
        self.path_rate_limits = path_rate_limits or {}
        self.window_size = window_size
        self.block_duration = block_duration

        # 使用双端队列存储全局请求时间戳
        self.global_requests = deque()

        # 使用字典存储每个IP的请求时间戳
        self.ip_requests = defaultdict(deque)

        # 使用字典存储每个路径的请求时间戳
        self.path_requests = defaultdict(deque)

        # 被封禁的IP及其解封时间
        self.blocked_ips = {
            # IP地址: 解封时间
            # "127.0.0.1": time.time() + 60 * 60 * 24,  # 封禁一天
            # "localhost": time.time() + 60 * 60 * 24,  # 封禁一天
        }

        # 用于线程安全的锁
        self.lock = threading.RLock()

        logger.debug(
            f"限流中间件初始化: 全局限流={global_rate_limit}/秒, IP限流={ip_rate_limit}/秒, 窗口大小={window_size}秒"
        )

    @suppress_errors
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("限流中间件")
        client_ip = self._get_client_ip(request)
        path = request.url.path
        current_time = time.time()

        # 检查IP是否被封禁
        if self._is_ip_blocked(client_ip, current_time):
            return self._create_rate_limit_response(
                client_ip=client_ip,
                path=path,
                reason="IP已被临时封禁",
                retry_after=int(self.blocked_ips[client_ip] - current_time),
            )

        # 应用限流策略
        with self.lock:
            # 清理过期的请求记录
            self._clean_expired_requests(current_time)

            # 检查是否超过限流阈值
            limit_check = self._check_rate_limits(client_ip, path)
            if limit_check:
                limit_type, current_count, limit = limit_check

                # 如果IP多次触发限流，临时封禁
                if limit_type == "ip" and current_count >= limit * 2:
                    self.blocked_ips[client_ip] = current_time + self.block_duration
                    logger.warning(f"IP {client_ip} 已被临时封禁 {self.block_duration} 秒，请求过于频繁")

                return self._create_rate_limit_response(
                    client_ip=client_ip, path=path, reason=f"{limit_type}限流触发", current=current_count, limit=limit
                )

            # 记录本次请求
            self._record_request(client_ip, path, current_time)

        # 设置请求开始时间（用于其他中间件）
        request.state.start_time = current_time

        # 处理请求
        response = await call_next(request)

        # 添加限流相关的响应头
        self._add_rate_limit_headers(response, client_ip, path)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_ip_blocked(self, ip: str, current_time: float) -> bool:
        """检查IP是否被封禁"""
        if ip in self.blocked_ips:
            if current_time > self.blocked_ips[ip]:
                with self.lock:
                    self.blocked_ips.pop(ip, None)
                return False
            return True
        return False

    def _clean_expired_requests(self, current_time: float) -> None:
        """清理过期的请求记录"""
        cutoff = current_time - self.window_size

        # 清理全局请求
        while self.global_requests and self.global_requests[0] < cutoff:
            self.global_requests.popleft()

        # 清理IP请求
        for ip, requests in list(self.ip_requests.items()):
            while requests and requests[0] < cutoff:
                requests.popleft()
            if not requests:
                self.ip_requests.pop(ip, None)

        # 清理路径请求
        for path, requests in list(self.path_requests.items()):
            while requests and requests[0] < cutoff:
                requests.popleft()
            if not requests:
                self.path_requests.pop(path, None)

    def _check_rate_limits(self, client_ip: str, path: str) -> Optional[Tuple[str, int, int]]:
        """
        检查是否超过限流阈值

        Returns:
            如果超过限流阈值，返回(限流类型, 当前请求数, 限流阈值)
            如果未超过限流阈值，返回None
        """
        # 检查全局限流
        if len(self.global_requests) >= self.global_rate_limit:
            return "全局", len(self.global_requests), self.global_rate_limit

        # 检查IP限流
        if client_ip in self.ip_requests and len(self.ip_requests[client_ip]) >= self.ip_rate_limit:
            return "IP", len(self.ip_requests[client_ip]), self.ip_rate_limit

        # 检查路径限流
        for prefix, limit in self.path_rate_limits.items():
            if path.startswith(prefix):
                if prefix in self.path_requests and len(self.path_requests[prefix]) >= limit:
                    return "路径", len(self.path_requests[prefix]), limit

        return None

    def _record_request(self, client_ip: str, path: str, timestamp: float) -> None:
        """记录请求"""
        self.global_requests.append(timestamp)
        self.ip_requests[client_ip].append(timestamp)

        for prefix in self.path_rate_limits:
            if path.startswith(prefix):
                self.path_requests[prefix].append(timestamp)

    def _create_rate_limit_response(
        self, client_ip: str, path: str, reason: str, retry_after: int = 1, current: int = None, limit: int = None
    ) -> JSONResponse:
        """创建限流响应"""
        logger = get_logger("限流中间件")
        message = f"请求被限流: {reason}"
        if current is not None and limit is not None:
            message += f", 当前请求数: {current}/{limit}"

        logger.warning(f"{message}, IP: {client_ip}, 路径: {path}")

        response = JSONResponse(
            status_code=429, content={"status": "error", "message": message, "data": {"retry_after": retry_after}}
        )

        # 添加标准的限流响应头
        response.headers["Retry-After"] = str(retry_after)

        return response

    def _add_rate_limit_headers(self, response: Response, client_ip: str, path: str) -> None:
        """添加限流相关的响应头"""
        with self.lock:
            # 添加全局限流信息
            global_remaining = max(0, self.global_rate_limit - len(self.global_requests))
            response.headers["X-RateLimit-Limit"] = str(self.global_rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(global_remaining)

            # 添加IP限流信息
            if client_ip in self.ip_requests:
                ip_remaining = max(0, self.ip_rate_limit - len(self.ip_requests[client_ip]))
                response.headers["X-RateLimit-IP-Limit"] = str(self.ip_rate_limit)
                response.headers["X-RateLimit-IP-Remaining"] = str(ip_remaining)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """超时中间件"""

    def __init__(self, app, timeout: float = 10.0):
        logger = get_logger("超时中间件")
        super().__init__(app)
        self.timeout = timeout
        logger.debug(f"超时中间件已初始化，超时时间设置为 {timeout} 秒")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("超时中间件")
        logger.debug(f"【超时中间件】开始处理 {request.method} {request.url.path}")

        # 创建一个任务来处理请求
        task = asyncio.create_task(call_next(request))

        try:
            # 使用 asyncio.wait_for 来限制任务执行时间
            response = await asyncio.wait_for(task, timeout=self.timeout)
            logger.debug(f"【超时中间件】成功完成请求处理 {request.method} {request.url.path}")
            return response
        except asyncio.TimeoutError:
            # 如果任务还在运行，尝试取消它
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"【超时中间件】取消任务时发生错误: {str(e)}")

            logger.warning(f"【超时中间件】请求处理超时 (>{self.timeout}秒): {request.method} {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={"status": "error", "message": f"请求处理超时，超过 {self.timeout} 秒", "data": None},
            )
        except Exception as e:
            logger.error(f"【超时中间件】处理请求时发生错误: {str(e)}")
            return JSONResponse(status_code=500, content={"status": "error", "message": "服务器内部错误", "data": None})
