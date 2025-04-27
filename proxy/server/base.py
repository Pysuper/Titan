# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：base.py
@Author  ：PySuper
@Date    ：2025-04-27 22:58
@Desc    ：Titan base
"""
import asyncio
import datetime
import json
import os
import traceback
import uuid
from typing import Any, Dict, List, Optional, Union

import tornado.web
import tornado.websocket

from logic.config import get_logger

logger = get_logger(__name__)

from config.files import UPLOAD_DIR


class CustomHttp(tornado.web.RequestHandler):
    """
    自定义HTTP请求处理类，提供通用的请求处理功能
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初始化请求相关属性
        self.client_ip = self.request.remote_ip
        self.start_time = datetime.datetime.now()
        self._request_id = str(uuid.uuid4())

        # 设置默认HTTP响应头
        self.set_default_headers()

        # 记录请求日志
        logger.debug(
            f"收到请求==> [ID: {self._request_id}] 来自 {self.client_ip} - {self.request.method} {self.request.uri}"
        )

    def http_err(self, msg: str, status_code: int = 400) -> None:
        """
        返回HTTP错误响应

        @param msg: 错误信息
        @param status_code: HTTP状态码，默认为400
        :return: None
        """
        logger.error(f"HTTP错误 [{self._request_id}]: {msg}")
        self.set_status(status_code)
        self.write({"status": "error", "message": msg, "request_id": self._request_id})
        return None

    def http_success(self, data: Any = None, message: str = "操作成功") -> None:
        """
        返回HTTP成功响应

        @param data: 响应数据
        @param message: 成功消息
        :return: None
        """
        response = {"status": "success", "message": message, "request_id": self._request_id}

        if data is not None:
            response["data"] = data

        self.write(response)
        return None

    def ws_err(self, msg: str) -> None:
        """
        返回WebSocket错误响应

        @param msg: 错误信息
        :return: None
        """
        logger.error(f"WebSocket错误 [{self._request_id}]: {msg}")
        self.write({"status": "error", "message": msg, "request_id": self._request_id})
        return None

    def set_default_headers(self) -> None:
        """
        设置跨域和安全相关的HTTP响应头
        """
        super().set_default_headers()

        # 跨域相关设置
        origin = self.request.headers.get("Origin", "*")
        self.set_header("Access-Control-Allow-Origin", origin)
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Access-Control-Max-Age", "3600")  # 预检请求缓存时间

        # 合并请求头
        default_headers = "Content-Type, Content-Length, Authorization, Accept, X-Requested-With, X-File-Name, Cache-Control, devicetype"
        request_headers = self.request.headers.get("Access-Control-Request-Headers", "")
        allowed_headers = default_headers + (f", {request_headers}" if request_headers else "")
        self.set_header("Access-Control-Allow-Headers", allowed_headers)

        # 安全相关设置
        self.set_header("X-XSS-Protection", "1; mode=block")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "SAMEORIGIN")
        self.set_header("Content-Security-Policy", "default-src * 'self' 'unsafe-inline' 'unsafe-eval' data: blob:")

        # 内容类型设置
        content_type = "text/plain" if self.request.method == "OPTIONS" else "application/json; charset=UTF-8"
        self.set_header("Content-Type", content_type)

    def options(self, *args, **kwargs) -> None:
        """
        处理OPTIONS请求，设置跨域和安全相关的HTTP响应头
        """
        # 设置响应状态码为204，表示请求已成功处理，但没有响应体
        self.set_status(204)
        self.finish()

    def get_ws(self) -> Optional[tornado.websocket.WebSocketHandler]:
        """
        获取WebSocket处理器

        :return: WebSocket处理器实例或None
        """
        ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
        return ws_handler_map.get("websocket_id")

    def save(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        保存上传的文件

        @param files: 上传的文件列表
        :return: 保存的文件信息列表
        """
        saved_files = []

        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        for file_data in files:
            original_filename = file_data["filename"]
            file_content = file_data["body"]
            content_type = file_data["content_type"]

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}_{original_filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            try:
                with open(file_path, "wb") as f:
                    f.write(file_content)

                file_info = {
                    "original_name": original_filename,
                    "saved_name": filename,
                    "file_path": file_path,
                    "file_size": len(file_content),
                    "content_type": content_type,
                    "upload_time": timestamp,
                    "unique_id": unique_id,
                }
                saved_files.append(file_info)
                logger.info(f"文件已保存: {file_path}")
            except IOError as e:
                error_msg = f"保存文件 {original_filename} 时出错: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())

        return saved_files

    def notify_ws(self, data: Dict[str, Any]) -> bool:
        """
        向WebSocket客户端发送通知

        @param data: 通知数据
        :return: 发送是否成功
        """
        try:
            ws = self.get_ws()
            if ws:
                # 添加时间戳和请求ID
                data.update({"timestamp": datetime.datetime.now().isoformat(), "request_id": self._request_id})

                if ws.send_message(json.dumps(data, ensure_ascii=False)):
                    logger.debug(f"通知WebSocket客户端成功: {self._request_id}")
                    return True
                else:
                    logger.warning(f"通知WebSocket客户端失败: {self._request_id}")
                    return False
            else:
                logger.warning("未找到WebSocket连接")
                return False
        except Exception as e:
            logger.error(f"通知WebSocket客户端时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    def extract_params(self) -> Dict[str, Any]:
        """
        提取请求参数，支持JSON和表单数据

        :return: 参数字典
        """
        params = {}

        # 尝试解析JSON请求体
        if self.request.body:
            try:
                request_data = json.loads(self.request.body)
                if isinstance(request_data, dict):
                    params.update(request_data)
            except json.JSONDecodeError:
                logger.warning(f"无法解析请求体为JSON [{self._request_id}]，尝试从form数据获取参数")

        # 获取URL查询参数
        for name, values in self.request.arguments.items():
            if values and len(values) > 0:
                # 解码字节字符串为普通字符串
                decoded_value = values[0].decode("utf-8") if isinstance(values[0], bytes) else values[0]
                params[name] = decoded_value

        # 尝试从表单数据获取参数
        for field_name, field_value in self.request.arguments.items():
            if field_name not in params or not params[field_name]:
                value = self.get_argument(field_name, None)
                if value:
                    params[field_name] = value

        logger.debug(f"提取的参数: {params}")
        return params

    def validate_params(self, required_params: List[str]) -> Union[Dict[str, Any], None]:
        """
        验证请求参数是否包含所有必需的参数

        @param required_params: 必需参数列表
        :return: 参数字典或None（如果验证失败）
        """
        params = self.extract_params()
        missing_params = [param for param in required_params if param not in params or not params[param]]

        if missing_params:
            self.http_err(f"缺少必需参数: {', '.join(missing_params)}", 400)
            return None

        return params

    def handle_exception(self, func):
        """
        异常处理装饰器

        @param func: 要装饰的函数
        :return: 装饰后的函数
        """

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"处理请求时发生错误: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                self.http_err(error_msg, 500)
                return None

        return wrapper


class CustomWebSocket(tornado.websocket.WebSocketHandler):
    """
    自定义WebSocket处理类，提供通用的WebSocket处理功能
    """

    def __init__(self, application, request):
        super().__init__(application, request)
        self.client_id = None
        self.start_time = None
        self.client_ip = None
        self.bytes_received = None
        self.message_count = None
        self.bytes_sent = None
        self.current_frame_index = None
        self.is_paused = None
        self.stop_tasks = None
        self.connected_at = None
        self._request_id = None
        self.frame_task = None
        self.heartbeat_future = None
        self.last_pong = None
        self.ping_timeout = None
        self.ping_interval = None
        self.is_processing_queue = None
        self.message_queue = None
        self.user_data = None
        self.is_authenticated = None
        self.holdon = None

    def initialize(self, *args, **kwargs):
        # 注册WebSocket处理器
        if "ws_handlers" not in self.application.settings:
            self.application.settings["ws_handlers"] = []
        self.application.settings["ws_handlers"].append(self)

        # 使用多个websocket还是一个websocket
        self.holdon = kwargs.get("holdon", False)

        # WebSocket连接状态
        self.is_authenticated = False
        self.user_data = {}

        # 消息队列
        self.message_queue = asyncio.Queue()
        self.is_processing_queue = False

        # 心跳检测
        self.ping_interval = kwargs.get("ping_interval", 30)  # 默认30秒发送一次ping
        self.ping_timeout = kwargs.get("ping_timeout", 60)  # 默认60秒未收到pong则断开
        self.last_pong = datetime.datetime.now()
        self.heartbeat_future = None

        # 连接管理
        self.frame_task = None
        self.stop_tasks = False
        self.is_paused = True
        self.current_frame_index = 0

        # 统计信息
        self.message_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.connected_at = datetime.datetime.now()

        # 初始化WebSocket相关属性
        self.client_ip = self.request.remote_ip
        self.start_time = datetime.datetime.now()
        self._request_id = str(uuid.uuid4())

        # 记录WebSocket连接日志
        logger.info(f"WebSocket连接成功: [ID: {self._request_id}] 来自 {self.client_ip}")

    def open(self):
        """
        WebSocket连接建立时的处理函数
        功能:
            1. 管理WebSocket连接实例
            2. 处理旧连接的清理
            3. 初始化新连接的状态
            4. 启动心跳检测任务
            5. 启动消息队列处理任务
        """
        if self.holdon:
            self.open_save()
        else:
            self.open_remove()

        # 启动心跳检测
        self.start_heartbeat()

        # 启动消息队列处理
        asyncio.create_task(self.process_message_queue())

    def open_save(self):
        """
        保持每个WebSocket连接
        """
        # 不再关闭旧连接，而是将每个新连接都保存在列表中
        self.client_id = str(uuid.uuid4())

        # 将当前连接添加到ws_map中，使用client_id作为key
        ws_map = self.application.settings.setdefault("ws_handler_map", {})
        ws_map[self.client_id] = self

        # 同时将当前连接添加到websocket_id列表，保持向后兼容
        if "websocket_id" not in ws_map:
            ws_map["websocket_id"] = self

        self.stop_tasks = False
        # # -1是因为包含websocket_id键
        logger.info(f"WebSocket已连接，客户端ID: {self.client_id}，当前活跃连接数: {len(ws_map)-1}")

    def open_remove(self):
        """
        每次只保留一个WebSocket连接
        """
        try:
            # 获取WebSocket处理器映射
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})

            # 处理已存在的连接
            self._cleanup_existing_connection(ws_handler_map)

            # 初始化新连接
            self.client_id = str(uuid.uuid4())
            ws_handler_map["websocket_id"] = self
            self.stop_tasks = False

            # 记录连接信息
            client_info = {
                "id": self.client_id,
                "ip": self.request.remote_ip,
                "time": datetime.datetime.now().isoformat(),
                "user_agent": self.request.headers.get("User-Agent", "未知"),
            }
            logger.info(f"WebSocket已连接: {json.dumps(client_info, ensure_ascii=False)}")

            # 发送欢迎消息
            welcome_message = {
                "type": "connection_established",
                "client_id": self.client_id,
                "server_time": datetime.datetime.now().isoformat(),
                "message": "WebSocket连接已建立",
            }
            asyncio.create_task(self._safe_write_message(json.dumps(welcome_message, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"WebSocket连接建立过程中出错: {str(e)}", exc_info=True)
            # 尝试关闭连接
            try:
                self.close()
            except:
                pass

    @staticmethod
    def _cleanup_existing_connection(ws_handler_map):
        """
        清理已存在的WebSocket连接

        @param ws_handler_map: WebSocket处理器映射
        """
        old_handler = ws_handler_map.get("websocket_id")
        if old_handler:
            logger.info(f"WebSocket(ID: {getattr(old_handler, 'client_id', 'unknown')})已存在, 正在关闭...")

            try:
                old_handler.stop_tasks = True
                if hasattr(old_handler, "frame_task") and old_handler.frame_task and not old_handler.frame_task.done():
                    old_handler.frame_task.cancel()
                    logger.debug("已取消旧连接的帧任务")

                # 取消心跳检测任务
                if hasattr(old_handler, "heartbeat_future") and old_handler.heartbeat_future:
                    old_handler.heartbeat_future.cancel()
                    logger.debug("已取消旧连接的心跳检测任务")

                close_message = {
                    "type": "connection_closed",
                    "reason": "新的客户端连接已建立",
                    "server_time": datetime.datetime.now().isoformat(),
                }
                try:
                    old_handler.write_message(json.dumps(close_message, ensure_ascii=False))
                except Exception as e:
                    logger.warning(f"发送关闭消息时出错: {str(e)}")

                # 关闭连接
                old_handler.close(code=1000, reason="新的客户端连接已建立")
                logger.debug("旧的WebSocket连接已成功关闭")
            except Exception as e:
                logger.warning(f"关闭旧的WebSocket连接时出错: {str(e)}")

    def on_message(self, message: str):
        """
        处理从客户端接收的WebSocket消息

        支持的操作:
        - auth: 身份验证
        - message: 普通消息
        - event: 事件通知
        - command: 命令执行
        - ping: 心跳检测

        @param message: 客户端发送的消息
        """
        try:
            # 更新统计信息
            self.message_count += 1
            self.bytes_received += len(message)

            # 更新最后一次收到消息的时间
            self.last_pong = datetime.datetime.now()

            # 解析消息
            data = tornado.escape.json_decode(message)
            logger.info(f"收到客户端消息: {json.dumps(data, ensure_ascii=False)}")

            # 心跳消息直接处理
            if data.get("type") == "ping":
                return self._handle_ping(data)

            # 将消息加入队列异步处理
            asyncio.create_task(self.message_queue.put(data))

        except json.JSONDecodeError:
            logger.error("接收到无效的JSON格式消息")
            return self._send_response("error", "无效的JSON格式")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            return self._send_response("error", f"处理消息时出错: {str(e)}")

    async def process_message_queue(self):
        """处理消息队列中的消息"""
        if self.is_processing_queue:
            return

        self.is_processing_queue = True
        try:
            while not self.stop_tasks:
                try:
                    # 等待新消息，超时1秒
                    data = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)

                    # 检查连接状态
                    if not self.ws_connection:
                        logger.warning("WebSocket连接已关闭，停止处理消息队列")
                        break

                    # 处理消息
                    await self._process_message(data)

                    # 标记任务完成
                    self.message_queue.task_done()
                except asyncio.TimeoutError:
                    # 超时，继续下一次循环
                    continue
                except Exception as e:
                    logger.error(f"处理队列消息时出错: {str(e)}", exc_info=True)
        finally:
            self.is_processing_queue = False

    async def _process_message(self, data):
        """处理单条消息"""
        # 如果没有type字段，返回通用响应
        if "type" not in data:
            return await self._send_response("received", "消息已收到")

        # 身份验证消息特殊处理
        if data["type"] == "auth" and not self.is_authenticated:
            return await self._handle_auth(data)

        # 其他消息类型需要身份验证（可根据需要调整）
        if not self.is_authenticated and data["type"] != "ping":
            return await self._send_response("error", "请先进行身份验证", type="auth_required")

        # 根据type分发到对应的处理方法
        msg_type = data["type"]
        type_handlers = {
            "message": self._handle_message,
            "event": self._handle_event,
            "command": self._handle_command,
        }

        # 调用对应的处理方法
        handler = type_handlers.get(msg_type)
        if handler:
            return await handler(data)

        logger.warning(f"未知的消息类型: {msg_type}")
        return await self._send_response("warning", f"未知的消息类型: {msg_type}")

    async def _handle_auth(self, data):
        """处理身份验证"""
        # TODO: 这里仅为示例实现，实际应用中应该使用更安全的身份验证方式
        token = data.get("token")
        if not token:
            return await self._send_response("error", "缺少身份验证令牌", type="auth_failed")

        # 这里添加实际的身份验证逻辑
        # 演示简单验证: 令牌长度大于10
        if len(token) > 10:
            self.is_authenticated = True
            self.user_data = {
                "auth_time": datetime.datetime.now().isoformat(),
                "client_id": self.client_id,
                # 可以添加其他用户数据
            }
            return await self._send_response("success", "身份验证成功", type="auth_success", user_data=self.user_data)
        else:
            return await self._send_response("error", "无效的身份验证令牌", type="auth_failed")

    async def _handle_message(self, data):
        """处理普通消息"""
        # 可以根据需要处理不同类型的普通消息
        content = data.get("content", "")
        target = data.get("target", "all")

        # 广播消息
        if target == "all" and getattr(self, "is_authenticated", False):
            return await self._broadcast_message(content, exclude_self=data.get("exclude_self", False))

        # 私聊消息
        if target != "all" and target:
            return await self._send_private_message(target, content)

        return await self._send_response("success", "消息已接收", type="message_received")

    async def _handle_event(self, data):
        """处理事件通知"""
        event_name = data.get("event_name")
        event_data = data.get("event_data", {})

        if not event_name:
            return await self._send_response("error", "缺少事件名称", type="event_error")

        # 处理特定事件
        # 这里可以添加具体事件的处理逻辑
        logger.info(f"收到事件: {event_name}, 数据: {json.dumps(event_data, ensure_ascii=False)}")

        return await self._send_response(
            "success", f"事件 {event_name} 已处理", type="event_processed", event_name=event_name
        )

    async def _handle_command(self, data):
        """处理命令执行"""
        command = data.get("command")
        params = data.get("params", {})

        if not command:
            return await self._send_response("error", "缺少命令", type="command_error")

        # 处理特定命令
        # 这里可以添加具体命令的处理逻辑
        logger.info(f"执行命令: {command}, 参数: {json.dumps(params, ensure_ascii=False)}")

        # 根据命令名执行操作
        command_result = self.do_status(command)

        if command_result:
            return await self._send_response(
                "success", "命令已执行", type="command_executed", command=command, result=command_result
            )
        else:
            return await self._send_response("error", f"未知命令: {command}", type="command_error")

    async def _handle_ping(self, data):
        """处理心跳消息"""
        pong_data = {
            "type": "pong",
            "time": datetime.datetime.now().isoformat(),
            "server_id": self._request_id,
        }
        await self._safe_write_message(json.dumps(pong_data, ensure_ascii=False))
        return True

    async def async_send_response(self, status, message, **kwargs):
        """
        发送统一格式的响应(异步版本)

        @param status: 状态 (success/error/warning/received)
        @param message: 消息内容
        @param kwargs: 其他要包含在响应中的字段
        :return: 是否发送成功
        """
        res = {"status": status, "message": message}
        res.update(kwargs)
        return await self._safe_write_message(json.dumps(res, ensure_ascii=False))

    def _send_response(self, status, message, **kwargs):
        """
        发送统一格式的响应(同步版本)

        @param status: 状态 (success/error/warning/received)
        @param message: 消息内容
        @param kwargs: 其他要包含在响应中的字段
        :return: 是否发送成功
        """
        res = {"status": status, "message": message}
        res.update(kwargs)
        return self.send_message(json.dumps(res, ensure_ascii=False))

    def send_message(self, message):
        """发送消息到WebSocket客户端"""
        try:
            if not self.ws_connection:
                logger.warning("尝试发送消息，但WebSocket连接已关闭")
                return False

            # 更新统计信息
            self.bytes_sent += len(message) if isinstance(message, str) else len(str(message))

            self.write_message(message)
            return True
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False

    def response(self, status, message, **kwargs):
        """
        发送统一格式的响应

        @param status: 状态 (success/error/warning/received)
        @param message: 消息内容
        @param kwargs: 其他要包含在响应中的字段
        :return: 是否发送成功
        """
        res = {"status": status, "message": message}
        res.update(kwargs)
        return self.send_message(json.dumps(res, ensure_ascii=False))

    async def _broadcast_message(self, content, exclude_self=False):
        """广播消息到所有连接"""
        try:
            if not self.application.settings.get("ws_handlers"):
                return await self._send_response("warning", "没有可用的WebSocket连接")

            broadcast_data = {
                "type": "broadcast",
                "content": content,
                "sender": self.client_id,
                "timestamp": datetime.datetime.now().isoformat(),
            }

            message_json = json.dumps(broadcast_data, ensure_ascii=False)
            sent_count = 0

            for handler in self.application.settings["ws_handlers"]:
                if exclude_self and handler == self:
                    continue

                if getattr(handler, "is_authenticated", False) and handler.ws_connection:
                    if await handler._safe_write_message(message_json):
                        sent_count += 1

            return await self._send_response(
                "success", f"消息已广播给 {sent_count} 个连接", type="broadcast_sent", recipients_count=sent_count
            )

        except Exception as e:
            logger.error(f"广播消息时出错: {str(e)}", exc_info=True)
            return await self._send_response("error", f"广播消息时出错: {str(e)}")

    async def _send_private_message(self, target_id, content):
        """发送私聊消息"""
        try:
            ws_map = self.application.settings.get("ws_handler_map", {})
            target_handler = ws_map.get(target_id)

            if not target_handler or not target_handler.ws_connection:
                return await self._send_response("error", f"目标用户 {target_id} 不在线", type="message_error")

            private_data = {
                "type": "private_message",
                "content": content,
                "sender": self.client_id,
                "timestamp": datetime.datetime.now().isoformat(),
            }

            message_json = json.dumps(private_data, ensure_ascii=False)
            if await target_handler._safe_write_message(message_json):
                return await self._send_response("success", "私聊消息已发送", type="message_sent", recipient=target_id)
            else:
                return await self._send_response("error", "私聊消息发送失败", type="message_error")

        except Exception as e:
            logger.error(f"发送私聊消息时出错: {str(e)}", exc_info=True)
            return await self._send_response("error", f"发送私聊消息时出错: {str(e)}")

    def start_heartbeat(self):
        """启动心跳检测"""

        async def heartbeat_check():
            while not self.stop_tasks:
                try:
                    # 发送ping消息
                    ping_data = {"type": "ping", "time": datetime.datetime.now().isoformat()}
                    await self._safe_write_message(json.dumps(ping_data, ensure_ascii=False))

                    # 检查上次收到pong的时间
                    elapsed = (datetime.datetime.now() - self.last_pong).total_seconds()
                    if elapsed > self.ping_timeout:
                        logger.warning(f"WebSocket连接 {self.client_id} 心跳超时 ({elapsed}秒)")
                        # self.close(code=1001, reason="心跳超时")
                        self.close()
                        break

                    # 等待下一次心跳
                    await asyncio.sleep(self.ping_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"心跳检测出错: {str(e)}", exc_info=True)
                    await asyncio.sleep(5)  # 出错后等待5秒重试

        self.heartbeat_future = asyncio.create_task(heartbeat_check())

    def get_connection_stats(self):
        """获取连接统计信息"""
        now = datetime.datetime.now()
        uptime = (now - self.connected_at).total_seconds()

        return {
            "client_id": self.client_id,
            "ip": self.client_ip,
            "connected_at": self.connected_at.isoformat(),
            "uptime_seconds": uptime,
            "messages_received": self.message_count,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "authenticated": self.is_authenticated,
            "queue_size": self.message_queue.qsize() if hasattr(self, "message_queue") else 0,
        }

    def stop_sending(self):
        """停止所有发送任务"""
        try:
            # 设置停止标志
            self.stop_tasks = True

            # 取消帧任务
            if self.frame_task and not self.frame_task.done():
                self.frame_task.cancel()

            # 取消心跳检测任务
            if self.heartbeat_future and not self.heartbeat_future.done():
                self.heartbeat_future.cancel()

            # 重置状态
            self.is_paused = True

            # 发送状态通知
            status_notification = self._create_status_notification("stopped")
            asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))

            logger.info("已停止所有发送任务")
            return True
        except Exception as e:
            logger.error(f"停止发送任务时出错: {str(e)}", exc_info=True)
            return False

    async def _safe_write_message(self, message):
        """
        安全地发送WebSocket消息

        @param message: 要发送的消息
        :return: 是否发送成功
        """
        try:
            if not self.ws_connection:
                logger.warning("尝试发送消息，但WebSocket连接已关闭")
                return False

            # 更新统计信息
            self.bytes_sent += len(message) if isinstance(message, str) else len(str(message))

            self.write_message(message)
            return True
        except tornado.websocket.WebSocketClosedError:
            logger.warning("WebSocket连接已关闭，无法发送消息")
            return False
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False

    def on_close(self):
        """WebSocket连接关闭时的处理函数"""
        try:
            # 停止所有任务
            self.stop_sending()

            # 从处理器映射中移除
            if hasattr(self.application, "settings") and "ws_handler_map" in self.application.settings:
                ws_handler_map = self.application.settings["ws_handler_map"]
                if ws_handler_map.get("websocket_id") == self:
                    ws_handler_map.pop("websocket_id", None)

                # 移除client_id映射
                if hasattr(self, "client_id") and self.client_id in ws_handler_map:
                    ws_handler_map.pop(self.client_id, None)

            # 从处理器列表中移除
            if hasattr(self.application, "settings") and "ws_handlers" in self.application.settings:
                if self in self.application.settings["ws_handlers"]:
                    self.application.settings["ws_handlers"].remove(self)

            # 记录连接统计信息
            stats = self.get_connection_stats()
            logger.info(f"WebSocket已关闭，连接统计: {json.dumps(stats, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"处理WebSocket关闭时出错: {str(e)}", exc_info=True)

    def do_status(self, action):
        """
        接收不同的状态命令，执行相应的操作
        @param action: 状态命令
        :return: 处理结果
        """
        action_handlers = {
            "do": lambda: {"status": "success", "message": "执行成功"},
            "stats": lambda: self.get_connection_stats(),
            "clear_queue": lambda: self._clear_message_queue(),
            "ping": lambda: {"ping_time": datetime.datetime.now().isoformat()},
        }

        handler = action_handlers.get(action)
        if handler:
            return handler()
        return None

    def _clear_message_queue(self):
        """清空消息队列"""
        try:
            while not self.message_queue.empty():
                self.message_queue.get_nowait()
                self.message_queue.task_done()
            return {"status": "success", "message": "消息队列已清空"}
        except Exception as e:
            logger.error(f"清空消息队列时出错: {str(e)}")
            return {"status": "error", "message": f"清空消息队列时出错: {str(e)}"}

    def check_origin(self, origin):
        """检查请求来源"""
        # 这里可以实现跨域验证逻辑
        # 默认允许所有来源
        return True


class FileStream(tornado.iostream.IOStream):
    """
    自定义的文件流类，用于处理文件的读取和写入操作
    """

    def get(self, file_path):
        """
        根据请求URL，找到视频文件，返回数据
        如：http://localhost:9000/files/person.mp4

        :param file_path: 通过路由捕获的文件路径部分
        """
        if not file_path:
            self.set_status(400)
            self.write("File path is required")
            return

        file_path = os.path.join(UPLOAD_DIR, file_path)
        if not os.path.exists(file_path):
            self.set_status(404)
            self.write("File not found")
            return

        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")

        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                self.write(chunk)
        self.finish()

    def __init__(self, file_path, chunk_size=1024 * 1024):
        """
        初始化文件流
        @param file_path: 文件路径
        @param chunk_size: 每次读取的块大小
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.file = None
        self.total_size = 0
        self.read_offset = 0

    def open(self):
        """
        打开文件
        :return: 是否成功打开文件
        """
        try:
            self.file = open(self.file_path, "rb")
            self.total_size = os.path.getsize(self.file_path)  # 获取文件大小
            return True
        except IOError as e:
            logger.error(f"打开文件时出错: {str(e)}")
            return False

    def close(self):
        """
        关闭文件
        :return: 是否成功关闭文件
        """
        try:
            if self.file:
                self.file.close()
                return True
        except IOError as e:
            logger.error(f"关闭文件时出错: {str(e)}")
            return False
        return False

    def read(self):
        """
        读取文件内容
        :return: 文件内容
        """
        if not self.file:
            return None
        self.file.seek(self.read_offset)
        data = self.file.read(self.chunk_size)
        self.read_offset += len(data)
        return data

    def is_eof(self):
        """
        判断是否到达文件末尾
        :return: 是否到达文件末尾
        """
        return self.read_offset >= self.total_size


class VideoStreamHandler(tornado.web.RequestHandler):
    """
    视频流处理类，用于处理视频文件的流式传输
    """

    async def get(self):
        """
        处理GET请求，用于流式传输视频文件
        """
        video_path = self.get_argument("path", None)
        if not video_path:
            self.set_status(400)
            self.write("缺少参数: path")
            return

        # 打开视频文件
        video_stream = FileStream(video_path)
        if not video_stream.open():
            self.set_status(404)
            self.write("找不到视频文件")
            return

        # 设置响应头
        self.set_header("Content-Type", "video/mp4")
        self.set_header("Content-Disposition", f"attachment; filename={os.path.basename(video_path)}")  # 文件名
        # 开始流式传输
        while not video_stream.is_eof():
            data = video_stream.read()
            if not data:
                break
            await self.write(data)
            await self.flush()

        # 关闭文件
        video_stream.close()
