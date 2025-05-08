"""
@Project ：Backend
@File    ：message.py
@Author  ：PySuper
@Date    ：2025/4/23 20:34
@Desc    ：处理消息中间件
"""

import asyncio
import json
import threading
import time
from collections import deque
from queue import PriorityQueue
from typing import Any, List
from typing import Callable, Dict

import aiohttp
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logic.config import get_logger

logger = get_logger("middleware")


class Message:
    def __init__(self, content: Any, priority: int = 0, timestamp: float = None):
        self.content = content
        self.priority = priority
        self.timestamp = timestamp or time.time()

    def __lt__(self, other):
        return self.priority > other.priority


class MessageMiddleware:
    """
    消息中间件

    1、基本的消息队列操作: 发送消息、获取消息、查看消息、清空消息队列等。
    2、优先级队列: 可以发送带优先级的消息,并通过get_priority_message()获取优先级最高的消息。
    3、消息订阅: 允许其他对象订阅消息,当有新消息时会通知所有订阅者。
    4、消息过滤: 可以根据条件筛选或移除消息。
    5、批量处理: 可以批量获取或处理所有消息。
    6、线程安全: 使用锁来确保在多线程环境下的安全操作。
    """

    def __init__(self):
        self._messages = deque()
        self._priority_queue = PriorityQueue()
        self._subscribers = []
        self._lock = threading.Lock()

    def send_message(self, message: Any, priority: int = 0):
        """
        发送消息
        @param message: 消息内容
        @param priority: 消息优先级 (越大优先级越高)
        """
        with self._lock:
            msg = Message(message, priority)
            self._messages.append(msg)
            self._priority_queue.put(msg)
        self._notify_subscribers(msg)

    def get_message(self) -> Any:
        """
        获取下一条消息 (FIFO顺序)
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._messages.popleft().content if self._messages else None

    def get_priority_message(self) -> Any:
        """
        获取下一条优先级最高的消息
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._priority_queue.get().content if not self._priority_queue.empty() else None

    def peek_message(self) -> Any:
        """
        查看下一条消息但不移除
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._messages[0].content if self._messages else None

    def get_all_messages(self) -> List[Any]:
        """
        获取所有消息
        :return: 消息列表
        """
        with self._lock:
            messages = [msg.content for msg in self._messages]
            self._messages.clear()
            while not self._priority_queue.empty():
                self._priority_queue.get()
        return messages

    def clear_messages(self):
        """
        清空消息队列
        """
        with self._lock:
            self._messages.clear()
            while not self._priority_queue.empty():
                self._priority_queue.get()

    def message_count(self) -> int:
        """
        获取消息数量
        :return: 消息数量
        """
        return len(self._messages)

    def subscribe(self, callback: Callable[[Message], None]):
        """
        订阅消息
        @param callback: 接收消息的回调函数
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Message], None]):
        """
        取消订阅
        @param callback: 要取消的回调函数
        """
        self._subscribers.remove(callback)

    def _notify_subscribers(self, message: Message):
        """
        通知所有订阅者
        @param message: 要广播的消息
        """
        for subscriber in self._subscribers:
            subscriber(message)

    def filter_messages(self, condition: Callable[[Any], bool]) -> List[Any]:
        """
        根据条件筛选消息
        @param condition: 筛选条件函数
        :return: 符合条件的消息列表
        """
        with self._lock:
            return [msg.content for msg in self._messages if condition(msg.content)]

    def remove_messages(self, condition: Callable[[Any], bool]):
        """
        根据条件移除消息
        @param condition: 移除条件函数
        """
        with self._lock:
            self._messages = deque([msg for msg in self._messages if not condition(msg.content)])
            new_priority_queue = PriorityQueue()
            while not self._priority_queue.empty():
                msg = self._priority_queue.get()
                if not condition(msg.content):
                    new_priority_queue.put(msg)
            self._priority_queue = new_priority_queue

    def process_messages(self, processor: Callable[[Any], None]):
        """
        处理所有消息
        @param processor: 处理消息的函数
        """
        while True:
            message = self.get_message()
            if message is None:
                break
            processor(message)


class ResponseSerializerMiddleware(BaseHTTPMiddleware):
    """响应序列化中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if response.headers.get("content-type") == "application/json":
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                data = json.loads(body)
                if not isinstance(data, dict) or not all(k in data for k in ["status", "message"]):
                    data = {"status": "success", "message": "操作成功", "data": data}

                return JSONResponse(content=data, status_code=response.status_code, headers=dict(response.headers))
            except json.JSONDecodeError:
                logger.warning("无法解析响应体为JSON")
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    异常处理中间件
    1、捕获所有异常并返回统一的错误响应。
    2、记录异常信息和堆栈跟踪。
    3、返回错误响应时包含错误码和错误信息。
    4、可以根据不同的异常类型返回不同的错误码和错误信息。
    5、可以根据不同的环境（开发、测试、生产）返回不同的错误信息。
    6、可以根据不同的请求路径返回不同的错误信息。

    TODO: 和全局异常处理器功能相似，但有以下区别：
    1、全局异常处理器是在整个应用程序中捕获所有异常的入口点，而中间件可以在请求处理的不同阶段捕获异常。
    2、全局异常处理器可以返回自定义的响应，而中间件只能返回默认的响应。
    3、全局异常处理器可以根据不同的环境（开发、测试、生产）返回不同的响应，而中间件只能返回默认的响应。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"【异常处理中间件】 请求处理异常: {str(e)}")

            # 输出堆栈跟踪信息
            # logger.debug(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"服务器内部错误: {str(e)}", "data": None},
            )


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    # 定义性能等级阈值（秒）
    PERFORMANCE_THRESHOLDS = {
        "normal": 0.5,  # 正常请求
        "slow": 1.0,  # 慢请求
        "very_slow": 2.0,  # 非常慢的请求
    }

    # @suppress_errors
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("性能监控中间件")
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 记录处理时间到响应头
        response.headers["X-Process-Time"] = str(process_time)

        # 获取请求信息
        request_info = f"{request.method} {request.url.path}"

        # 根据处理时间分级记录日志
        if process_time <= self.PERFORMANCE_THRESHOLDS["normal"]:
            logger.debug(f"【性能监控】 请求 {request_info} 处理时间: {process_time:.4f}秒")
        elif process_time <= self.PERFORMANCE_THRESHOLDS["slow"]:
            logger.info(f"【性能监控】 慢请求: {request_info} 处理时间: {process_time:.4f}秒")
        elif process_time <= self.PERFORMANCE_THRESHOLDS["very_slow"]:
            logger.warning(f"【性能监控】 较慢请求: {request_info} 处理时间: {process_time:.4f}秒")
        else:
            logger.error(f"【性能监控】 极慢请求: {request_info} 处理时间: {process_time:.4f}秒")

        # 添加额外的性能指标到响应头
        self._add_performance_metrics(response, process_time)

        return response

    def _add_performance_metrics(self, response: Response, process_time: float):
        """添加额外的性能指标到响应头"""
        # 性能等级
        if process_time <= self.PERFORMANCE_THRESHOLDS["normal"]:
            performance_level = "normal"
        elif process_time <= self.PERFORMANCE_THRESHOLDS["slow"]:
            performance_level = "slow"
        elif process_time <= self.PERFORMANCE_THRESHOLDS["very_slow"]:
            performance_level = "very_slow"
        else:
            performance_level = "critical"

        response.headers["X-Performance-Level"] = performance_level


class TrafficMonitorMiddleware(BaseHTTPMiddleware):
    """流量监控中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.start_time = time.time()
        self.path_stats = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        self.request_count += 1
        path = request.url.path

        if path not in self.path_stats:
            self.path_stats[path] = {"count": 0, "total_time": 0}

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        self.path_stats[path]["count"] += 1
        self.path_stats[path]["total_time"] += process_time

        if self.request_count % 100 == 0:
            elapsed = time.time() - self.start_time
            rps = self.request_count / elapsed if elapsed > 0 else 0
            logger.info(f"流量统计: 总请求数: {self.request_count}, 运行时间: {elapsed:.2f}秒, RPS: {rps:.2f}")

            for p, stats in sorted(self.path_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
                avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
                logger.info(f"路径统计: {p}, 请求数: {stats['count']}, 平均处理时间: {avg_time:.4f}秒")

        return response


class TrafficSchedulerMiddleware(BaseHTTPMiddleware):
    """流量调度中间件"""

    def __init__(self, app, priority_paths: Dict[str, int] = None):
        super().__init__(app)
        self.priority_paths = priority_paths or {}
        self.request_queues = {}
        self.processing = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        priority = 5  # 默认优先级

        for prefix, prio in self.priority_paths.items():
            if path.startswith(prefix):
                priority = prio
                break

        if priority >= 8:
            return await call_next(request)

        future = asyncio.Future()
        if priority not in self.request_queues:
            self.request_queues[priority] = []
        self.request_queues[priority].append((request, call_next, future))

        if not self.processing:
            asyncio.create_task(self._process_queues())

        return await future

    async def _process_queues(self):
        """处理请求队列"""
        self.processing = True

        try:
            while any(self.request_queues.values()):
                for priority in sorted(self.request_queues.keys(), reverse=True):
                    if self.request_queues[priority]:
                        request, call_next, future = self.request_queues[priority].pop(0)

                        try:
                            response = await call_next(request)
                            future.set_result(response)
                        except Exception as e:
                            future.set_exception(e)

                        await asyncio.sleep(0)
                        break
                else:
                    break
        finally:
            self.processing = False


class TrafficForwardingMiddleware(BaseHTTPMiddleware):
    """流量转发中间件"""

    def __init__(self, app, target_url: str):
        super().__init__(app)
        self.target_url = target_url

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api"):
            return await self._forward_request(request)
        return await call_next(request)

    async def _forward_request(self, request: Request) -> Response:
        async with request.body() as body:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=self.target_url + request.url.path,
                    headers=request.headers,
                    data=body,
                ) as response:
                    return Response(
                        content=await response.read(),
                        status_code=response.status,
                        headers=response.headers,
                        media_type=response.content_type,
                    )


class RoutingMiddleware(BaseHTTPMiddleware):
    """URL 路由中间件"""

    def __init__(self, app, routes: Dict[str, Callable[[Request], Response]]):
        super().__init__(app)
        self.routes = routes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.routes:
            return await self.routes[request.url.path](request)
        return await call_next(request)
