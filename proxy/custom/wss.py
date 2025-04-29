"""
@Project ：Titan
@File    ：wss.py
@Author  ：PySuper
@Date    ：2025/4/28 11:38
@Desc    ：Titan WebSocket服务器实现
"""

import asyncio
import datetime
import json
import uuid
from typing import Dict, Any

import tornado.web
import tornado.websocket

from logic.config import get_logger

logger = get_logger("proxy-server")


class CustomWebSocket(tornado.websocket.WebSocketHandler):
    """
    自定义WebSocket处理类，提供高性能的WebSocket通信功能

    特性:
    - 支持多连接模式和单连接模式
    - 自动心跳检测和连接维护
    - 消息队列异步处理
    - 身份验证机制
    - 消息广播与私聊
    - 连接状态监控
    """

    # 消息类型处理映射
    MESSAGE_TYPES = {
        "auth": "_handle_auth",
        "message": "_handle_message",
        "event": "_handle_event",
        "command": "_handle_command",
        "ping": "_handle_ping",
    }

    # 状态响应类型
    STATUS_TYPES = ["success", "error", "warning", "info", "received"]

    def __init__(self, application, request, *args, **kwargs):
        """初始化WebSocket连接处理器"""
        super().__init__(application, request)

        # 连接标识和会话信息
        self.client_id: str = ""
        self._request_id: str = str(uuid.uuid4())
        self.client_ip: str = ""
        self.user_data: Dict[str, Any] = {}
        self.is_authenticated: bool = False

        # 连接统计数据
        self.connected_at: datetime.datetime = ""
        self.start_time: datetime.datetime = ""
        self.bytes_received: int = 0
        self.bytes_sent: int = 0
        self.message_count: int = 0

        # 消息处理队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_processing_queue: bool = False

        # 心跳检测
        self._ping_interval: int = 30
        self._ping_timeout: int = 60
        self.last_pong: datetime.datetime = datetime.datetime.now()
        self.heartbeat_future: asyncio.Task = ""

        # 任务控制
        self.frame_task: asyncio.Task = ""
        self.stop_tasks: bool = False
        self.is_paused: bool = True

        # 连接模式 (True: 允许多连接, False: 单连接模式)
        self.holdon: bool = True

    def initialize(self, *args, **kwargs):
        """初始化连接配置和状态"""
        # 注册到WebSocket处理器集合
        if "ws_handlers" not in self.application.settings:
            self.application.settings["ws_handlers"] = []
        self.application.settings["ws_handlers"].append(self)

        # 设置连接模式
        self.holdon = kwargs.get("holdon", True)  # 默认为允许多连接

        # 初始化连接状态
        self.is_authenticated = False  # 默认已认证
        self.user_data = {}  # 默认用户数据为空

        # 配置心跳检测参数
        self.heartbeat_enabled = kwargs.get("heartbeat_enabled", False)  # 是否启用心跳检测
        self._ping_interval = kwargs.get("ping_interval", 30)  # 心跳检测间隔
        self._ping_timeout = kwargs.get("ping_timeout", 60)  # 心跳检测超时
        self.last_pong = datetime.datetime.now()  # 最后一次收到心跳回复的时间

        # 初始化任务控制状态
        self.stop_tasks = False  # 任务停止标志
        self.is_paused = True  # 任务暂停标志

        # 初始化统计数据
        self.message_count = 0  # 消息计数
        self.bytes_received = 0  # 接收字节数
        self.bytes_sent = 0  # 发送字节数
        self.connected_at = datetime.datetime.now()  # 连接时间

        # 设置连接基本信息
        self.client_ip = self.request.remote_ip  # 客户端IP地址
        self.start_time = datetime.datetime.now()  # 连接开始时间
        self._request_id = str(uuid.uuid4())  # 请求ID

        # 记录连接日志
        # logger.info(f"WebSocket Client: 🔌 [ID: {self._request_id}] 来自 {self.client_ip}")

    # 取绑定了当前请求ID的logger
    def _log(self):
        """获取绑定了当前请求ID的logger"""
        return logger.bind(request_id=self._request_id)

    # 连接建立事件
    def open(self):
        """处理WebSocket连接建立事件"""
        # 根据连接模式处理连接
        self._handle_multi_connection() if self.holdon else self._handle_single_connection()

        # 启动心跳检测
        if self.heartbeat_enabled:
            self._start_heartbeat()

        # 启动消息队列处理
        asyncio.create_task(self._process_message_queue())
        # logger.debug(f"ws连接初始化: [ID: {self.client_id}]")

    # 处理多连接模式 - 保留所有连接
    def _handle_multi_connection(self):
        """处理多连接模式 - 保留所有连接"""
        # 生成唯一客户端ID
        self.client_id = str(uuid.uuid4())

        # 注册连接到连接映射表
        ws_map = self.application.settings.setdefault("ws_handler_map", {})
        ws_map[self.client_id] = self

        # 保持向后兼容
        if "websocket_id" not in ws_map:
            ws_map["websocket_id"] = self

        # 活跃连接数 (减1是因为包含websocket_id键)
        active_connections = len(ws_map) - 1
        logger.info(f"ws新客户端: ID={self.client_id}, 当前连接数={active_connections}")

    # 处理单连接模式 - 保留最新连接
    def _handle_single_connection(self):
        """处理单连接模式 - 保留最新连接"""
        try:
            # 获取连接映射表
            ws_map = self.application.settings.setdefault("ws_handler_map", {})

            # 关闭已存在的连接
            self._close_existing_connection(ws_map)

            # 建立新连接
            self.client_id = str(uuid.uuid4())
            ws_map["websocket_id"] = self

            # 记录连接信息
            client_info = {
                "id": self.client_id,
                "ip": self.request.remote_ip,
                "time": datetime.datetime.now().isoformat(),
                "user_agent": self.request.headers.get("User-Agent", "未知"),
            }
            logger.debug(f"WebSocket已连接: {json.dumps(client_info, ensure_ascii=False)}")

            # 发送欢迎消息
            welcome = {
                "type": "connection_established",
                "client_id": self.client_id,
                "server_time": datetime.datetime.now().isoformat(),
                "message": "WebSocket已连接",
            }
            self._async_write_message(welcome)

        except Exception as e:
            logger.error(f"建立连接时出错: {str(e)}", exc_info=True)
            self.close(code=1011, reason="连接初始化失败")

    # 关闭已存在的连接
    def _close_existing_connection(self, ws_map):
        """关闭已存在的连接"""
        old_handler = ws_map.get("websocket_id")
        if not old_handler:
            return

        logger.debug(f"关闭旧连接: ID={getattr(old_handler, 'client_id', 'unknown')}")
        try:
            # 停止任务
            old_handler.stop_tasks = True

            # 取消帧任务
            if hasattr(old_handler, "frame_task") and old_handler.frame_task:
                old_handler.frame_task.cancel()

            # 取消心跳任务
            if hasattr(old_handler, "heartbeat_future") and old_handler.heartbeat_future:
                old_handler.heartbeat_future.cancel()

            # 发送关闭通知
            close_msg = {
                "type": "connection_closed",
                "reason": "新的客户端连接已建立，旧连接已关闭",
                "server_time": datetime.datetime.now().isoformat(),
            }
            old_handler.write_message(json.dumps(close_msg, ensure_ascii=False))

            # 关闭连接
            old_handler.close(code=1000, reason="新的客户端连接已建立，旧连接已关闭")

        except Exception as e:
            logger.warning(f"关闭旧连接时出错: {str(e)}")

    # 接收处理WebSocket消息
    def on_message(self, message: str):
        """处理接收到的WebSocket消息"""
        # 消息为空检查
        if not message:
            return self._send_error("收到空消息")

        try:
            # 更新统计信息
            self.message_count += 1
            self.bytes_received += len(message) if hasattr(message, "__len__") else 0
            self.last_pong = datetime.datetime.now()

            # 解析消息
            data = tornado.escape.json_decode(message)
            if not isinstance(data, dict):
                return self._send_error("无效的消息格式")

            # 记录消息
            logger.debug(f"收到消息: {json.dumps(data, ensure_ascii=False)}")

            # 处理心跳消息
            if data.get("type") == "ping" or data.get("action") == "heartbeat":
                return self._handle_ping(data)

            # 将消息加入队列异步处理
            asyncio.create_task(self.message_queue.put(data))
            return None

        except json.JSONDecodeError:
            logger.error("接收到无效的JSON格式消息")
            return self._send_error("无效的JSON格式")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            return self._send_error(f"处理消息时出错: {str(e)}")

    # TODO：处理消息队列
    async def _process_message_queue(self):
        """处理消息队列"""
        if self.is_processing_queue:
            return

        self.is_processing_queue = True
        log = logger.bind(request_id=self._request_id)  # 使用绑定了request_id的logger
        try:
            while not self.stop_tasks:
                try:
                    # 等待新消息，超时1秒
                    data = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)

                    # 检查连接状态
                    if not self.ws_connection:
                        log.warning("WebSocket连接已关闭，停止处理消息队列")
                        break

                    # 处理消息
                    if data is not None:
                        await self._process_message(data)

                    # 标记任务完成
                    self.message_queue.task_done()

                except asyncio.TimeoutError:
                    # 超时，继续下一次循环
                    continue
                except Exception as e:
                    log.error(f"处理队列消息时出错: {str(e)}", exc_info=True)
                    # 尝试标记任务完成
                    try:
                        self.message_queue.task_done()
                    except Exception:
                        pass
        finally:
            self.is_processing_queue = False

    # 处理单条消息
    async def _process_message(self, data: Dict[str, Any]):
        """处理单条消息"""
        try:
            # 数据类型检查
            if not isinstance(data, dict):
                await self._send_response("error", "无效的消息格式")
                return

            # 处理action字段（兼容不同格式的消息）
            if "action" in data and "type" not in data:
                action_type_map = {
                    "heartbeat": "ping",
                    "auth": "auth",
                    "message": "message",
                    "command": "command",
                    "event": "event",
                }
                data["type"] = action_type_map.get(data["action"], data["action"])

            # 确保消息类型存在
            msg_type = data.get("type")
            if not msg_type:
                await self._send_response("received", "消息已收到")
                return

            # 身份验证特殊处理
            if msg_type == "auth" and not self.is_authenticated:
                await self._handle_auth(data)
                return

            # 心跳消息特殊处理
            if msg_type == "ping" or data.get("action") == "heartbeat":
                await self._handle_ping(data)
                return

            # 其他消息类型需要身份验证
            if not self.is_authenticated and msg_type not in ["ping"]:
                await self._send_response("error", "请先进行身份验证", type="auth_required")
                return

            # 根据类型分发处理
            handler_name = self.MESSAGE_TYPES.get(msg_type)
            if handler_name and hasattr(self, handler_name):
                await getattr(self, handler_name)(data)
            else:
                logger.warning(f"未知的消息类型: {msg_type}")
                await self._send_response("warning", f"未知的消息类型: {msg_type}")

        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            await self._send_response("error", f"处理消息时出错: {str(e)}")

    # 处理身份验证请求
    async def _handle_auth(self, data: Dict[str, Any]):
        """处理身份验证请求"""
        try:
            token = data.get("token")
            if not token:
                await self._send_response("error", "缺少身份验证令牌", type="auth_failed")
                return

            # 简单的身份验证逻辑，实际应用中应实现更安全的机制
            if len(token) > 10:
                self.is_authenticated = True
                self.user_data = {
                    "auth_time": datetime.datetime.now().isoformat(),
                    "client_id": self.client_id,
                }
                await self._send_response("success", "身份验证成功", type="auth_success", user_data=self.user_data)
            else:
                await self._send_response("error", "无效的身份验证令牌", type="auth_failed")
        except Exception as e:
            logger.error(f"身份验证处理出错: {str(e)}", exc_info=True)
            await self._send_response("error", f"身份验证处理出错", type="auth_error")

    # 处理普通消息
    async def _handle_message(self, data: Dict[str, Any]):
        """处理普通消息"""
        try:
            content = data.get("content", "")
            target = data.get("target", "all")

            # 广播消息
            if target == "all":
                await self._broadcast_message(content, exclude_self=data.get("exclude_self", False))
                return

            # 私聊消息
            if target != "all" and target:
                await self._send_private_message(target, content)
                return

            await self._send_response("success", "消息已接收", type="message_received")
        except Exception as e:
            logger.error(f"消息处理出错: {str(e)}", exc_info=True)
            await self._send_response("error", "消息处理出错", type="message_error")

    # 处理事件通知
    async def _handle_event(self, data: Dict[str, Any]):
        """处理事件通知"""
        try:
            event_name = data.get("event_name")
            event_data = data.get("event_data", {})

            if not event_name:
                await self._send_response("error", "缺少事件名称", type="event_error")
                return

            # 记录事件
            logger.info(f"收到事件: {event_name}, 数据: {json.dumps(event_data, ensure_ascii=False)}")

            # 实际项目中可以在这里添加事件处理逻辑
            await self._send_response(
                "success",
                f"事件 {event_name} 已处理",
                type="event_processed",
                event_name=event_name,
            )
        except Exception as e:
            logger.error(f"事件处理出错: {str(e)}", exc_info=True)
            await self._send_response("error", "事件处理出错", type="event_error")

    # 处理命令执行
    async def _handle_command(self, data: Dict[str, Any]):
        """处理命令执行"""
        try:
            command = data.get("command")
            params = data.get("params", {})

            if not command:
                await self._send_response("error", "缺少命令", type="command_error")
                return

            # 记录命令
            logger.info(f"执行命令: {command}, 参数: {json.dumps(params, ensure_ascii=False)}")

            # 执行命令
            command_result = self._execute_command(command, params)

            if command_result:
                await self._send_response(
                    "success",
                    "命令已执行",
                    type="command_executed",
                    command=command,
                    result=command_result,
                )
            else:
                await self._send_response("error", f"未知命令: {command}", type="command_error")
        except Exception as e:
            logger.error(f"命令处理出错: {str(e)}", exc_info=True)
            await self._send_response("error", "命令处理出错", type="command_error")

    # 执行命令并返回结果
    def _execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行命令并返回结果"""
        command_handlers = {
            "stats": self.get_connection_stats,
            "clear_queue": self._clear_message_queue,
            "ping": lambda: {"ping_time": datetime.datetime.now().isoformat()},
            "status": self._get_status,
        }

        handler = command_handlers.get(command)
        if handler:
            return handler()
        return None

    # 获取服务器状态信息
    def _get_status(self) -> Dict[str, Any]:
        """获取服务器状态信息"""
        return {
            "status": "running",
            "uptime": (datetime.datetime.now() - self.connected_at).total_seconds(),
            "authenticated": self.is_authenticated,
            "message_count": self.message_count,
        }

    # 处理心跳消息
    async def _handle_ping(self, data: Dict[str, Any]):
        """处理心跳消息"""
        pong_data = {
            "type": "pong",
            "time": datetime.datetime.now().isoformat(),
            "server_id": self._request_id,
        }
        await self._safe_write_message(json.dumps(pong_data, ensure_ascii=False))
        return None

    # 启动心跳检测任务
    def _start_heartbeat(self):
        """启动心跳检测任务"""

        async def heartbeat_check():
            while not self.stop_tasks:
                try:
                    # 发送ping消息
                    ping_data = {"type": "ping", "time": datetime.datetime.now().isoformat()}
                    await self._safe_write_message(json.dumps(ping_data, ensure_ascii=False))

                    # 检查上次响应时间
                    elapsed = (datetime.datetime.now() - self.last_pong).total_seconds()

                    # 超时检测
                    if elapsed > self._ping_timeout:
                        logger.warning(f"WebSocket连接 {self.client_id} 心跳超时 ({elapsed}秒)")
                        self.close(code=1001, reason="心跳超时")
                        break

                    # 等待下一次心跳
                    await asyncio.sleep(self._ping_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"心跳检测出错: {str(e)}")
                    await asyncio.sleep(5)  # 出错后等待5秒重试

        self.heartbeat_future = asyncio.create_task(heartbeat_check())

    # 广播消息到所有连接
    async def _broadcast_message(self, content: str, exclude_self: bool = False):
        """广播消息到所有连接"""
        try:
            handlers = self.application.settings.get("ws_handlers", [])
            if not handlers:
                await self._send_response("warning", "没有可用的WebSocket连接")
                return

            broadcast_data = {
                "type": "broadcast",
                "content": content,
                "sender": self.client_id,
                "timestamp": datetime.datetime.now().isoformat(),
            }

            message_json = json.dumps(broadcast_data, ensure_ascii=False)
            sent_count = 0

            for handler in handlers:
                if exclude_self and handler == self:
                    continue

                if getattr(handler, "is_authenticated", False) and handler.ws_connection:
                    await handler._safe_write_message(message_json)
                    sent_count += 1

            await self._send_response(
                "success", f"消息已广播给 {sent_count} 个连接", type="broadcast_sent", recipients_count=sent_count
            )
        except Exception as e:
            logger.error(f"广播消息时出错: {str(e)}", exc_info=True)
            await self._send_response("error", "广播消息时出错")

    # 发送私聊消息
    async def _send_private_message(self, target_id: str, content: str):
        """发送私聊消息"""
        try:
            ws_map = self.application.settings.get("ws_handler_map", {})
            target_handler = ws_map.get(target_id)

            if not target_handler or not target_handler.ws_connection:
                await self._send_response("error", f"目标用户 {target_id} 不在线", type="message_error")
                return

            private_data = {
                "type": "private_message",
                "content": content,
                "sender": self.client_id,
                "timestamp": datetime.datetime.now().isoformat(),
            }

            await target_handler._safe_write_message(json.dumps(private_data, ensure_ascii=False))
            await self._send_response("success", "私聊消息已发送", type="message_sent", recipient=target_id)
        except Exception as e:
            logger.error(f"发送私聊消息时出错: {str(e)}", exc_info=True)
            await self._send_response("error", "发送私聊消息时出错")

    # 发送统一格式的响应(异步版本)
    async def _send_response(self, status: str, message: str, **kwargs):
        """发送统一格式的响应(异步版本)"""
        try:
            res = {"status": status, "message": message}
            res.update(kwargs)
            await self._safe_write_message(json.dumps(res, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送响应时出错: {str(e)}")

    # 发送错误响应(同步版本)
    def _send_error(self, message: str, **kwargs) -> None:
        """发送错误响应(同步版本)"""
        self._send_message({"status": "error", "message": message, **kwargs})
        return None

    # 发送消息到WebSocket客户端
    def _send_message(self, data: Dict[str, Any]) -> bool:
        """发送消息到WebSocket客户端"""
        try:
            if not self.ws_connection:
                logger.warning("尝试发送消息，但WebSocket连接已关闭")
                return False

            message = json.dumps(data, ensure_ascii=False)

            # 更新统计信息
            self.bytes_sent += len(message)

            self.write_message(message)
            return True
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False

    # 异步发送JSON消息
    def _async_write_message(self, data: Dict[str, Any]):
        """异步发送JSON消息"""
        asyncio.create_task(self._safe_write_message(json.dumps(data, ensure_ascii=False)))

    # 安全地发送WebSocket消息
    async def _safe_write_message(self, message: str) -> bool:
        """安全地发送WebSocket消息"""
        try:
            if not self.ws_connection:
                logger.warning("尝试发送消息，但WebSocket连接已关闭")
                return False

            # 更新统计信息
            self.bytes_sent += len(message)

            self.write_message(message)
            return True
        except tornado.websocket.WebSocketClosedError:
            logger.warning("WebSocket连接已关闭，无法发送消息")
            return False
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False

    # 获取连接统计信息
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        try:
            if not self.connected_at:
                return {
                    "client_id": self.client_id,
                    "ip": self.client_ip,
                    "connected_at": "未连接",
                    "uptime_seconds": 0,
                    "messages_received": self.message_count,
                    "bytes_received": self.bytes_received,
                    "bytes_sent": self.bytes_sent,
                    "authenticated": self.is_authenticated,
                    "queue_size": self.message_queue.qsize() if hasattr(self, "message_queue") else 0,
                }

            uptime = (datetime.datetime.now() - self.connected_at).total_seconds()
            connected_at_iso = self.connected_at.isoformat() if self.connected_at else "未知"

            return {
                "client_id": self.client_id or "未知",
                "ip": self.client_ip or "未知",
                "connected_at": connected_at_iso,
                "uptime_seconds": uptime,
                "messages_received": self.message_count,
                "bytes_received": self.bytes_received,
                "bytes_sent": self.bytes_sent,
                "authenticated": self.is_authenticated,
                "queue_size": self.message_queue.qsize() if hasattr(self, "message_queue") else 0,
            }
        except Exception as e:
            # 出现异常时返回基本信息
            logger.error(f"获取连接统计信息出错: {str(e)}")
            return {
                "error": "获取连接统计信息失败",
                "client_id": getattr(self, "client_id", "未知"),
                "exception": str(e),
            }

    # 清空消息队列
    def _clear_message_queue(self) -> Dict[str, Any]:
        """清空消息队列"""
        try:
            # 安全地清空队列
            cleared_count = 0
            if hasattr(self, "message_queue") and self.message_queue:
                while not self.message_queue.empty():
                    try:
                        self.message_queue.get_nowait()
                        self.message_queue.task_done()
                        cleared_count += 1
                    except Exception as e:
                        logger.warning(f"清空单个消息时出错: {str(e)}")
                        break

            return {"status": "success", "message": "消息队列已清空", "cleared_messages": cleared_count}
        except Exception as e:
            logger.error(f"清空消息队列时出错: {str(e)}")
            return {"status": "error", "message": f"清空消息队列时出错: {str(e)}"}

    # 处理WebSocket连接关闭事件
    def on_close(self):
        """处理WebSocket连接关闭事件"""
        log = logger.bind(request_id=getattr(self, "_request_id", "unknown"))

        try:
            # 停止所有任务
            self.stop_tasks = True

            # 取消心跳任务
            if hasattr(self, "heartbeat_future") and self.heartbeat_future and not self.heartbeat_future.done():
                self.heartbeat_future.cancel()

            # 取消帧任务
            if hasattr(self, "frame_task") and self.frame_task and not self.frame_task.done():
                self.frame_task.cancel()

            # 清理消息队列
            self._clear_message_queue()

            # 从处理器映射中移除
            if (
                hasattr(self, "application")
                and hasattr(self.application, "settings")
                and "ws_handler_map" in self.application.settings
            ):
                ws_map = self.application.settings["ws_handler_map"]

                # 移除全局映射
                if ws_map.get("websocket_id") == self:
                    ws_map.pop("websocket_id", None)

                # 移除客户端ID映射
                if hasattr(self, "client_id") and self.client_id in ws_map:
                    ws_map.pop(self.client_id, None)

            # 从处理器列表中移除
            if (
                hasattr(self, "application")
                and hasattr(self.application, "settings")
                and "ws_handlers" in self.application.settings
            ):
                handlers = self.application.settings["ws_handlers"]
                if self in handlers:
                    handlers.remove(self)

            # 记录连接统计
            try:
                stats = self.get_connection_stats()
                log.info(f"WebSocket连接已断开 ❌ : {json.dumps(stats, ensure_ascii=False)}")
            except Exception as e:
                log.error(f"获取连接统计时出错: {str(e)}")

        except Exception as e:
            log.error(f"处理WebSocket关闭时出错: {str(e)}", exc_info=True)

    # 跨域验证逻辑
    def check_origin(self, origin: str) -> bool:
        """
        跨域验证逻辑，默认允许所有来源

        可以在此方法中实现域名白名单或其他安全验证
        """
        # TODO: 实现更安全的跨域验证
        return True
