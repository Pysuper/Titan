"""
@Project ：Titan
@File    ：websocket.py
@Author  ：PySuper
@Date    ：2025/4/25 13:52
@Desc    ：WebSocket Client
"""

import asyncio
import json
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

from proxy.config.logs import logger


class WebSocketState(Enum):
    """WebSocket连接状态枚举"""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    CLOSING = auto()


class WebSocketClient:
    """
    WebSocket客户端

    特性:
    - 自动重连机制
    - 消息处理器注册
    - 心跳检测
    - 消息队列
    - 连接状态管理
    - 异常处理
    """

    def __init__(
        self,
        uri: str,
        auto_reconnect: bool = True,
        reconnect_interval: float = 3.0,
        max_reconnect_attempts: int = 5,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
        receive_timeout: float = 1.0,
        extra_headers: Optional[Dict] = None,
    ):
        """
        初始化WebSocket客户端

        Args:
            uri: WebSocket服务器地址
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔(秒)
            max_reconnect_attempts: 最大重连尝试次数
            ping_interval: 心跳间隔(秒)
            ping_timeout: 心跳超时(秒)
            receive_timeout: 接收消息超时(秒)
            extra_headers: 额外的HTTP头信息
        """
        self.uri = uri
        self.state = WebSocketState.DISCONNECTED
        self.websocket = None
        self.should_exit = False

        # 重连配置
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_attempts = 0

        # 心跳配置
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.last_pong_time = 0

        # 接收配置
        self.receive_timeout = receive_timeout

        # 连接配置
        self.extra_headers = extra_headers

        # 消息处理
        self.message_handlers = {}
        self.default_message_handler = None

        # 任务管理
        self.tasks = []

        # 消息队列
        self.send_queue = asyncio.Queue()

        # 事件回调
        self.on_connect_callbacks = []
        self.on_disconnect_callbacks = []
        self.on_error_callbacks = []

    def on_connect(self, callback: Callable):
        """注册连接成功回调"""
        self.on_connect_callbacks.append(callback)
        return self

    def on_disconnect(self, callback: Callable):
        """注册断开连接回调"""
        self.on_disconnect_callbacks.append(callback)
        return self

    def on_error(self, callback: Callable):
        """注册错误回调"""
        self.on_error_callbacks.append(callback)
        return self

    def register_handler(self, message_type: str, handler: Callable[[Dict], Any]):
        """
        注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数，接收解析后的JSON消息
        """
        self.message_handlers[message_type] = handler
        return self

    def set_default_handler(self, handler: Callable[[Dict], Any]):
        """设置默认消息处理器"""
        self.default_message_handler = handler
        return self

    async def connect(self) -> bool:
        """
        连接到WebSocket服务器

        Returns:
            bool: 连接是否成功
        """
        if self.state in (WebSocketState.CONNECTED, WebSocketState.CONNECTING):
            return True

        self.state = WebSocketState.CONNECTING

        try:
            # 配置连接选项
            options = {
                "ping_interval": self.ping_interval,
                "ping_timeout": self.ping_timeout,
                "close_timeout": 5,
            }

            if self.extra_headers:
                options["extra_headers"] = self.extra_headers

            self.websocket = await websockets.connect(self.uri, **options)
            self.state = WebSocketState.CONNECTED
            self.reconnect_attempts = 0
            self.last_pong_time = time.time()

            logger.info(f"已连接: {self.uri}")

            # 启动任务
            self._start_tasks()

            # 触发连接回调
            for callback in self.on_connect_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self)
                    else:
                        callback(self)
                except Exception as e:
                    logger.error(f"连接回调执行错误: {str(e)}")

            return True
        except Exception as e:
            self.state = WebSocketState.DISCONNECTED
            error_msg = f"连接失败: {str(e)}"
            logger.error(error_msg)

            # 触发错误回调
            for callback in self.on_error_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self, error_msg)
                    else:
                        callback(self, error_msg)
                except Exception as e:
                    logger.error(f"错误回调执行错误: {str(e)}")

            return False

    async def disconnect(self):
        """断开WebSocket连接"""
        if self.state not in (WebSocketState.CONNECTED, WebSocketState.RECONNECTING):
            return

        self.state = WebSocketState.CLOSING

        # 取消所有任务
        self._cancel_tasks()

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"关闭连接时出错: {str(e)}")

        self.state = WebSocketState.DISCONNECTED
        logger.info("已断开连接")

        # 触发断开连接回调
        for callback in self.on_disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except Exception as e:
                logger.error(f"断开连接回调执行错误: {str(e)}")

    async def reconnect(self):
        """重新连接到WebSocket服务器"""
        if not self.auto_reconnect or self.should_exit:
            return False

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"重连失败: 已达到最大尝试次数 ({self.max_reconnect_attempts})")
            return False

        self.reconnect_attempts += 1
        self.state = WebSocketState.RECONNECTING

        logger.info(f"尝试重连 ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")

        # 确保旧连接已关闭
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass

        # 等待重连间隔
        await asyncio.sleep(self.reconnect_interval)

        # 尝试重新连接
        return await self.connect()

    async def send_message(self, message: Union[Dict, str, bytes]):
        """
        发送消息到WebSocket服务器

        Args:
            message: 要发送的消息，可以是字典、字符串或字节
        """
        # 将消息放入队列，由发送任务处理
        await self.send_queue.put(message)

    async def _send_worker(self):
        """消息发送工作线程"""
        while not self.should_exit:
            try:
                if self.state != WebSocketState.CONNECTED:
                    await asyncio.sleep(0.1)
                    continue

                # 从队列获取消息
                message = await self.send_queue.get()

                # 转换消息格式
                if isinstance(message, dict):
                    message = json.dumps(message, ensure_ascii=False)

                # 发送消息
                await self.websocket.send(message)

                # 标记任务完成
                self.send_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"发送消息时出错: {str(e)}")
                await asyncio.sleep(0.5)

    async def _receive_worker(self):
        """消息接收工作线程"""
        while not self.should_exit:
            try:
                if self.state != WebSocketState.CONNECTED:
                    await asyncio.sleep(0.1)
                    continue

                # 接收消息，设置超时
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=self.receive_timeout)

                    # 处理消息
                    await self._process_message(message)
                except asyncio.TimeoutError:
                    # 超时，继续循环
                    continue
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                logger.warning(f"连接已关闭: {str(e)}")

                if self.auto_reconnect and not self.should_exit:
                    await self.reconnect()
                else:
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"接收消息时出错: {str(e)}")

                if self.auto_reconnect and not self.should_exit:
                    await self.reconnect()
                else:
                    await asyncio.sleep(0.5)

    async def _heartbeat_worker(self):
        """心跳检测工作线程"""
        while not self.should_exit:
            try:
                if self.state != WebSocketState.CONNECTED:
                    await asyncio.sleep(1)
                    continue

                # 检查上次pong时间
                if time.time() - self.last_pong_time > self.ping_interval + self.ping_timeout:
                    logger.warning("心跳超时，尝试重连...")

                    if self.auto_reconnect:
                        await self.reconnect()

                await asyncio.sleep(self.ping_interval / 2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测时出错: {str(e)}")
                await asyncio.sleep(1)

    async def _process_message(self, message: str):
        """
        处理接收到的消息

        Args:
            message: 接收到的消息
        """
        try:
            # 尝试解析JSON
            data = json.loads(message)

            # 记录接收到的消息
            log_message = json.dumps(data, ensure_ascii=False)
            if len(log_message) > 100:
                log_message = log_message[:100] + "..."
            logger.info(f"接收到数据: {log_message}")

            # 根据消息类型调用对应的处理器
            message_type = data.get("type") or data.get("action") or data.get("status")

            if message_type and message_type in self.message_handlers:
                # 调用注册的处理器
                handler = self.message_handlers[message_type]
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            elif self.default_message_handler:
                # 调用默认处理器
                if asyncio.iscoroutinefunction(self.default_message_handler):
                    await self.default_message_handler(data)
                else:
                    self.default_message_handler(data)
            else:
                # 默认处理逻辑
                if data.get("status") == "ready":
                    await self.send_message({"action": "play_video"})
        except json.JSONDecodeError:
            logger.warning(f"非JSON格式消息: {message}")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")

    def _start_tasks(self):
        """启动所有工作任务"""
        self._cancel_tasks()  # 确保没有运行中的任务

        loop = asyncio.get_running_loop()

        # 创建工作任务
        self.tasks = [
            loop.create_task(self._send_worker()),
            loop.create_task(self._receive_worker()),
            loop.create_task(self._heartbeat_worker()),
        ]

    def _cancel_tasks(self):
        """取消所有工作任务"""
        for task in self.tasks:
            if not task.done():
                task.cancel()
        self.tasks = []

    def handle_exit(self):
        """处理退出信号"""
        self.should_exit = True
        logger.info("正在退出...")

        # 取消所有任务
        self._cancel_tasks()

    async def run(self):
        """运行WebSocket客户端"""
        if not await self.connect():
            if self.auto_reconnect:
                while self.reconnect_attempts < self.max_reconnect_attempts and not self.should_exit:
                    if await self.reconnect():
                        break
            else:
                return

        # 等待直到应该退出
        while not self.should_exit:
            await asyncio.sleep(0.1)

            # 检查连接状态
            if self.state == WebSocketState.DISCONNECTED and self.auto_reconnect:
                await self.reconnect()

        # 确保断开连接
        await self.disconnect()
