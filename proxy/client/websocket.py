"""
@Project ：Titan
@File    ：websocket.py
@Author  ：PySuper
@Date    ：2025/4/25 13:52
@Desc    ：WebSocket Client
"""

import argparse
import asyncio
import json
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

from logic.config import get_logger

logger = get_logger("proxy-websocket")


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
                "ping_interval": None,  # 禁用客户端自动ping，我们会自己处理
                "ping_timeout": None,  # 禁用ping超时检测
                "close_timeout": 5,
                "max_size": 10 * 1024 * 1024,  # 增大最大消息大小为10MB
                "max_queue": 32,  # 增大消息队列大小
                "open_timeout": 10,  # 连接超时增加到10秒
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
        logger.debug("已断开连接")

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

        logger.debug(f"尝试重连 ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")

        # 确保旧连接已关闭
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass

        # 重连间隔随重试次数增加
        backoff_time = self.reconnect_interval * (1.5 ** (self.reconnect_attempts - 1))
        backoff_time = min(backoff_time, 30)  # 最大30秒

        logger.info(f"等待 {backoff_time:.1f}秒后进行第 {self.reconnect_attempts} 次重连...")
        await asyncio.sleep(backoff_time)

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
                    # 使用锁或标志来确保同一时间只有一个协程调用recv
                    if not hasattr(self, "_recv_lock"):
                        self._recv_lock = asyncio.Lock()

                    async with self._recv_lock:
                        message = await asyncio.wait_for(self.websocket.recv(), timeout=self.receive_timeout)

                    # 收到任何消息都更新最后pong时间
                    self.last_pong_time = time.time()
                    # 处理消息
                    await self._process_message(message)
                except asyncio.TimeoutError:
                    # 超时，继续循环
                    continue
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                close_code = getattr(e, "code", 0)
                close_reason = getattr(e, "reason", "未知原因")

                # 如果是服务器主动关闭连接（例如新客户端连接），且关闭码为1000（正常关闭），不要立即重连
                if close_code == 1000 and "新的客户端连接" in str(close_reason):
                    logger.info(f"服务器主动关闭连接: {close_reason}")
                    # 等待一段时间，让新连接稳定
                    await asyncio.sleep(2)
                else:
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

                # 使用服务器能识别的操作类型发送心跳
                # 不使用ping操作，改用普通消息
                await self.send_message(
                    {"action": "heartbeat", "timestamp": time.time(), "client_info": {"type": "client_heartbeat"}}
                )

                # 检查上次pong时间
                elapsed = time.time() - self.last_pong_time
                if elapsed > self.ping_interval + self.ping_timeout:
                    logger.warning(f"心跳超时: 最后响应时间 {elapsed:.1f}秒前，尝试重连...")

                    if self.auto_reconnect:
                        await self.reconnect()

                # 等待到下一个心跳周期
                await asyncio.sleep(self.ping_interval)
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
            # 更新最后pong时间，表示连接活跃
            self.last_pong_time = time.time()

            # 检查是否为非JSON消息
            if not message or not message.strip():
                logger.debug("接收到空消息")
                return

            # 尝试解析JSON
            data = json.loads(message)

            # 记录接收到的消息
            log_message = json.dumps(data, ensure_ascii=False)
            if len(log_message) > 100:
                log_message = log_message[:100] + "..."
            # logger.debug(f"接收到数据: {log_message}")

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
            logger.warning(f"非JSON格式消息: {message[:100]}")
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
        try:
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
        except asyncio.CancelledError:
            logger.debug("接收到取消信号，正在退出...")
            self.should_exit = True
        except KeyboardInterrupt:
            logger.info("接收到键盘中断，正在退出...")
            self.should_exit = True
        except Exception as e:
            logger.error(f"运行时发生错误: {str(e)}")
        finally:
            # 确保断开连接
            await self.disconnect()
            await self.disconnect()


if __name__ == "__main__":

    # 参数解析
    parser = argparse.ArgumentParser(description="WebSocket客户端")
    parser.add_argument("--host", default="localhost", help="WebSocket服务器主机名")
    parser.add_argument("--port", type=int, default=9000, help="WebSocket服务器端口")
    parser.add_argument("--path", default="/api/websocket", help="WebSocket路径")
    parser.add_argument("--reconnect", type=int, default=10, help="最大重连次数")
    parser.add_argument("--ping", type=int, default=15, help="心跳间隔(秒)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()

    # 配置URI
    uri = f"ws://{args.host}:{args.port}{args.path}"

    # 如果不是调试模式，减少websockets的日志级别
    if not args.debug:
        import logging

        logging.getLogger("websockets").setLevel(logging.INFO)

    try:
        # 创建WebSocket客户端
        ws = WebSocketClient(
            uri=uri,
            auto_reconnect=True,
            max_reconnect_attempts=args.reconnect,
            reconnect_interval=2,
            receive_timeout=1.0,
            ping_interval=args.ping,
            ping_timeout=10,
        )

        # 定义消息处理函数
        def handle_message(data):
            status = data.get("status", "")
            msg = data.get("message", "")
            data_type = data.get("type", "")

            if status and msg:
                logger.debug(f"[{status}] {msg}")
            elif data_type:
                if data_type == "connection_established":
                    client_id = data.get("client_id", "未知")
                    logger.debug(f"[连接] 客户端ID: {client_id}")
                elif data_type == "connection_closed":
                    reason = data.get("reason", "未知原因")
                    logger.debug(f"[断开] 原因: {reason}")
                elif data_type == "status_change":
                    status = data.get("status", "未知")
                    logger.debug(f"[状态变更] 新状态: {status}")
                elif data_type == "frame_data":
                    frame = data.get("frame_index", 0)
                    total = data.get("total_frames", 0)
                    logger.debug(f"\r[帧数据] 进度: {frame}/{total} ({int(frame/total*100)}%)", end="")
                else:
                    logger.debug(f"[{data_type}] {json.dumps(data, ensure_ascii=False)[:100]}...")
            else:
                logger.debug(f"收到消息: {json.dumps(data, ensure_ascii=False)[:100]}...")

        # 注册默认消息处理器
        ws.set_default_handler(handle_message)

        # 注册连接事件处理
        # ws.on_connect(lambda _: print("\n已连接到服务器"))
        # ws.on_disconnect(lambda _: print("\n已断开连接"))
        # ws.on_error(lambda _, err: print(f"\n错误: {err}"))

        # 定义命令处理函数
        async def send_command(client, command):
            # 命令映射字典，将命令名称映射到对应的动作和参数处理函数
            command_map = {
                "play": {"action": "play_video"},
                "pause": {"action": "pause_video"},
                "resume": {"action": "resume_video"},
                "stop": {"action": "stop_video"},
                "replay": {"action": "replay_video"},
            }

            # 处理简单命令
            if command in command_map:
                await client.send_message(command_map[command])
                return True

            # 处理带参数的命令
            if command.startswith("set "):
                path = command[4:].strip()
                if not path:
                    print("错误: 请提供有效的视频路径")
                    return False
                await client.send_message({"action": "set_video_path", "video_path": path})
                return True

            # 处理JSON格式命令
            if command.startswith("{") and command.endswith("}"):
                try:
                    message = json.loads(command)
                    await client.send_message(message)
                    return True
                except json.JSONDecodeError:
                    print("错误: 无效的JSON格式")
                    return False

            # 未知命令
            print(f"未知命令: {command}")
            return False

        # 添加命令控制
        async def command_loop(client):
            # 显示可用命令帮助
            # print("\n可用命令:")
            # print("     play   - 播放视频")
            # print("     pause  - 暂停播放")
            # print("     resume - 恢复播放")
            # print("     stop   - 停止播放")
            # print("     replay - 重新播放")
            # print("     set <path> - 设置视频路径")
            # print("     exit/quit - 退出程序")
            # print("\n心跳检测:")
            # print(f"     间隔: {ws.ping_interval}秒")
            # print(f"     超时: {ws.ping_timeout}秒")
            print("\n自定义消息")
            print('     示例: {"action": "play_video"}')
            print('     身份验证: {"type": "auth", "token": "asdqwerfdsffsdfsdf", "action": "play_video"}')
            # print("\n正在等待命令...")

            while not client.should_exit:
                try:
                    # 使用异步输入，避免阻塞
                    command = await asyncio.to_thread(input, "\n请输入命令: \n")
                    command = command.strip().lower()

                    if command in ("exit", "quit", "q"):
                        print("正在退出...")
                        client.should_exit = True
                        break

                    if command:
                        await send_command(client, command)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"命令处理错误: {e}")

        # 启动命令循环
        async def run_with_command():
            # 创建任务
            connect_task = asyncio.create_task(ws.run())
            # command_task = asyncio.create_task(command_loop(ws))

            # 等待任务完成
            done, pending = await asyncio.wait([connect_task], return_when=asyncio.FIRST_COMPLETED)

            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info(f"WebSocket客户端已启动，按Ctrl+C或输入 exit/quit 退出...")

        # 启动客户端和命令循环
        asyncio.run(run_with_command())
    except KeyboardInterrupt:
        logger.critical("用户中断，程序退出")
    except Exception as e:
        logger.error(f"发生错误: {e}")
