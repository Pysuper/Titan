"""
@Project ：Titan
@File    ：ws.py
@Author  ：PySuper
@Date    ：2025/4/25 13:53
@Desc    ：Titan ws.py
"""

import asyncio
import datetime
import json
import uuid
from typing import Dict, Any

from logic.config import get_logger
from proxy.custom.wss import CustomWebSocket

# 创建一个WsProxy专用的日志器
ws_logger = get_logger("proxy")


class WsProxy(CustomWebSocket):
    """
    WebSocket代理类，用于处理WebSocket通信请求

    特性:
    - 支持多连接模式
    - 自定义消息处理
    - 视频控制命令处理
    - 状态同步
    - 事件通知
    """

    # 定义消息类型到处理方法的映射
    MESSAGE_TYPES = {
        "auth": "_handle_auth",
        "message": "_handle_message",
        "command": "_handle_command",
        "event": "_handle_event",
        "ping": "_handle_ping",
        "play_video": "_handle_play_video",
        "pause_video": "_handle_pause_video",
        "stop_video": "_handle_stop_video",
        "set_video_path": "_handle_set_video_path",
    }

    def __init__(self, *args, **kwargs):
        # 生成一个请求ID并绑定日志器
        self._request_id = str(uuid.uuid4())
        self.logger = ws_logger.bind(request_id=self._request_id)

        # 设置为多连接模式
        self.holdon = True

        # 视频状态
        self.video_state = {
            "status": "stopped",  # stopped, playing, paused
            "current_video": None,
            "position": 0,
            "duration": 0,
            "last_update": datetime.datetime.now().isoformat(),
        }

        # 初始化父类
        super().__init__(*args, **kwargs)

        # self.logger.info("WebSocket代理初始化完成")

    def open(self):
        """处理WebSocket连接打开事件"""
        # self.logger.info(f"WebSocket连接已打开: 客户端IP={self.client_ip}")

        # 调用父类方法处理基础连接逻辑
        super().open()

        # 发送欢迎消息
        welcome_message = {
            "type": "welcome",
            "message": "欢迎连接到Titan WebSocket服务",
            "server_time": datetime.datetime.now().isoformat(),
            "client_id": self.client_id,
        }
        self._send_message(welcome_message)

        # 发送当前状态
        # self._send_status_update()
        asyncio.create_task(self._send_status_update())

    def on_message(self, message: str):
        """处理接收到的WebSocket消息"""
        self.logger.debug(f"收到消息: {message[:100]}...")

        try:
            # 解析消息并添加到消息队列，让异步处理器处理
            data = json.loads(message)
            asyncio.create_task(self.message_queue.put(data))

            # 不再直接调用父类的on_message方法
            # 而是记录消息统计信息
            self.message_count += 1
            self.bytes_received += len(message)

        except json.JSONDecodeError:
            self.logger.error("收到无效的JSON消息")
            asyncio.create_task(self._send_response("error", "无效的JSON格式", type="json_error"))
        except Exception as e:
            self.logger.exception(f"处理消息时出错: {str(e)}")

    def on_close(self):
        """处理WebSocket连接关闭事件"""
        close_code = self.close_code if hasattr(self, "close_code") else None
        close_reason = self.close_reason if hasattr(self, "close_reason") else "未知原因"

        self.logger.info(f"WebSocket连接已关闭: 代码={close_code}, 原因={close_reason}")

        # 调用父类方法处理基础关闭逻辑
        super().on_close()

        # 清理资源
        self._cleanup_resources()

    def check_origin(self, origin):
        """检查请求来源是否允许连接"""
        # 在生产环境中应该实现更严格的来源检查
        self.logger.debug(f"检查连接来源: {origin}")
        return True  # 允许所有来源连接

    async def _handle_play_video(self, data: Dict[str, Any]):
        """处理播放视频命令"""
        video_path = data.get("video_path", self.video_state.get("current_video"))

        if not video_path:
            await self._send_response("error", "未指定视频路径", type="play_error")
            return

        self.logger.info(f"开始播放视频: {video_path}")

        # 更新视频状态
        self.video_state.update(
            {
                "status": "playing",
                "current_video": video_path,
                "position": data.get("position", 0),
                "last_update": datetime.datetime.now().isoformat(),
            }
        )

        # 发送状态更新
        await self._send_response(
            "success",
            "开始播放视频",
            type="video_status",
            status="playing",
            video_path=video_path,
            position=self.video_state["position"],
        )

        # 广播状态变更
        await self._broadcast_status_change()

    async def _handle_pause_video(self, data: Dict[str, Any]):
        """处理暂停视频命令"""
        if self.video_state["status"] != "playing":
            await self._send_response("error", "视频未在播放中", type="pause_error")
            return

        self.logger.info("暂停视频播放")

        # 更新视频状态
        self.video_state.update(
            {
                "status": "paused",
                "position": data.get("position", self.video_state["position"]),
                "last_update": datetime.datetime.now().isoformat(),
            }
        )

        # 发送状态更新
        await self._send_response(
            "success", "视频已暂停", type="video_status", status="paused", position=self.video_state["position"]
        )

        # 广播状态变更
        await self._broadcast_status_change()

    async def _handle_stop_video(self, data: Dict[str, Any]):
        """处理停止视频命令"""
        self.logger.info("停止视频播放")

        # 更新视频状态
        self.video_state.update(
            {
                "status": "stopped",
                "position": 0,
                "last_update": datetime.datetime.now().isoformat(),
            }
        )

        # 发送状态更新
        await self._send_response("success", "视频已停止", type="video_status", status="stopped")

        # 广播状态变更
        await self._broadcast_status_change()

    async def _handle_set_video_path(self, data: Dict[str, Any]):
        """处理设置视频路径命令"""
        video_path = data.get("video_path")

        if not video_path:
            await self._send_response("error", "未指定视频路径", type="set_path_error")
            return

        self.logger.info(f"设置视频路径: {video_path}")

        # 更新视频状态
        self.video_state.update(
            {
                "current_video": video_path,
                "position": 0,
                "last_update": datetime.datetime.now().isoformat(),
            }
        )

        # 发送状态更新
        await self._send_response("success", "视频路径已设置", type="video_path_set", video_path=video_path)

    async def _handle_command(self, data: Dict[str, Any]):
        """处理通用命令"""
        command = data.get("command")
        params = data.get("params", {})

        if not command:
            await self._send_response("error", "缺少命令名称", type="command_error")
            return

        self.logger.info(f"执行命令: {command}, 参数: {json.dumps(params, ensure_ascii=False)}")

        # 扩展的命令处理
        if command == "get_status":
            await self._send_status_update()
            return

        if command == "sync_clients":
            await self._broadcast_status_change()
            return

        # 调用父类的命令处理
        await super()._handle_command(data)

    async def _send_status_update(self):
        """发送当前状态更新"""
        # 添加服务器时间戳
        self.video_state["server_time"] = datetime.datetime.now().isoformat()

        # await self._send_response("success", "状态更新", type="status_update", **self.video_state)

        """发送当前状态更新"""
        # 添加服务器时间戳
        self.video_state["server_time"] = datetime.datetime.now().isoformat()

        # 创建一个不包含status键的副本
        video_state_copy = self.video_state.copy()
        if "status" in video_state_copy:
            # 将status值保存为video_status
            video_status = video_state_copy.pop("status")
            video_state_copy["video_status"] = video_status  # 使用不同的键名

        # 使用修改后的字典调用_send_response
        await self._send_response("success", "状态更新", type="status_update", **video_state_copy)

    async def _broadcast_status_change(self):
        """广播状态变更到所有连接的客户端"""
        # 获取WebSocket连接映射
        ws_map = self.application.settings.get("ws_handler_map", {})

        # 准备状态消息
        status_message = {
            "type": "status_change",
            "status": self.video_state["status"],
            "video_path": self.video_state["current_video"],
            "position": self.video_state["position"],
            "server_time": datetime.datetime.now().isoformat(),
        }

        # 转换为JSON字符串
        message_json = json.dumps(status_message, ensure_ascii=False)

        # 广播到所有客户端
        broadcast_count = 0
        for client_id, handler in ws_map.items():
            if client_id != "websocket_id" and handler != self:
                try:
                    handler.send_message(message_json)
                    broadcast_count += 1
                except Exception as e:
                    self.logger.error(f"广播状态到客户端 {client_id} 失败: {str(e)}")

        self.logger.info(f"状态变更已广播到 {broadcast_count} 个客户端")

    def _cleanup_resources(self):
        """清理资源"""
        # 如果有需要清理的资源，在这里实现
        pass

    def do_status(self, action=None, **kwargs):
        """
        处理状态操作，供外部调用

        Args:
            action: 操作名称，如play, pause, stop等
            **kwargs: 其他参数

        Returns:
            Dict: 操作结果
        """
        if action == "play":
            self.video_state.update(
                {
                    "status": "playing",
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )
            # 异步发送状态更新
            asyncio.create_task(self._broadcast_status_change())
            return {"status": "playing", "video": self.video_state["current_video"]}

        elif action == "pause":
            self.video_state.update(
                {
                    "status": "paused",
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )
            # 异步发送状态更新
            asyncio.create_task(self._broadcast_status_change())
            return {"status": "paused", "position": self.video_state["position"]}

        elif action == "stop":
            self.video_state.update(
                {
                    "status": "stopped",
                    "position": 0,
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )
            # 异步发送状态更新
            asyncio.create_task(self._broadcast_status_change())
            return {"status": "stopped"}

        elif action == "set_video":
            video_path = kwargs.get("video_path")
            if not video_path:
                return {"status": "error", "message": "未指定视频路径"}

            self.video_state.update(
                {
                    "current_video": video_path,
                    "position": 0,
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )
            # 异步发送状态更新
            asyncio.create_task(self._broadcast_status_change())
            return {"status": "ready", "video": video_path}

        elif action == "get_status":
            return {
                "status": self.video_state["status"],
                "video": self.video_state["current_video"],
                "position": self.video_state["position"],
                "duration": self.video_state["duration"],
                "last_update": self.video_state["last_update"],
            }

        elif action == "set_position":
            position = kwargs.get("position", 0)
            self.video_state["position"] = position
            self.video_state["last_update"] = datetime.datetime.now().isoformat()
            # 异步发送状态更新
            asyncio.create_task(self._broadcast_status_change())
            return {"status": self.video_state["status"], "position": position}

        elif action == "set_duration":
            duration = kwargs.get("duration", 0)
            self.video_state["duration"] = duration
            return {"status": "success", "duration": duration}

        else:
            self.logger.warning(f"未知的状态操作: {action}")
            return {"status": "error", "message": f"未知操作: {action}"}

    async def _process_message(self, data):
        """
        处理接收到的消息

        Args:
            data: 解析后的消息数据
        """
        # 获取消息类型
        msg_type = data.get("type") or data.get("action")

        if not msg_type:
            return await self._send_response("error", "消息缺少类型字段", type="message_error")

        # 查找对应的处理方法
        handler_name = self.MESSAGE_TYPES.get(msg_type)

        if handler_name and hasattr(self, handler_name):
            # 调用对应的处理方法
            handler = getattr(self, handler_name)
            return await handler(data)

        # 如果没有找到对应的处理方法，尝试使用父类的处理方法
        return await super()._process_message(data)

    def send_notification(self, notification_type, message, **kwargs):
        """
        发送通知消息

        Args:
            notification_type: 通知类型
            message: 通知消息
            **kwargs: 其他参数

        Returns:
            bool: 是否发送成功
        """
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            **kwargs,
        }

        try:
            self.send_message(json.dumps(notification, ensure_ascii=False))
            return True
        except Exception as e:
            self.logger.error(f"发送通知失败: {str(e)}")
            return False

    async def broadcast_notification(self, notification_type, message, **kwargs):
        """
        广播通知消息到所有客户端

        Args:
            notification_type: 通知类型
            message: 通知消息
            **kwargs: 其他参数

        Returns:
            int: 成功发送的客户端数量
        """
        # 获取WebSocket连接映射
        ws_map = self.application.settings.get("ws_handler_map", {})

        # 准备通知消息
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            **kwargs,
        }

        # 转换为JSON字符串
        message_json = json.dumps(notification, ensure_ascii=False)

        # 广播到所有客户端
        success_count = 0
        for client_id, handler in ws_map.items():
            if client_id != "websocket_id":
                try:
                    handler.send_message(message_json)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"广播通知到客户端 {client_id} 失败: {str(e)}")

        self.logger.info(f"通知已广播到 {success_count} 个客户端")
        return success_count

    def handle_video_event(self, event_type, **kwargs):
        """
        处理视频事件

        Args:
            event_type: 事件类型，如loaded, ended, error等
            **kwargs: 其他参数

        Returns:
            Dict: 处理结果
        """
        self.logger.info(f"处理视频事件: {event_type}")

        if event_type == "loaded":
            # 视频加载完成
            duration = kwargs.get("duration", 0)
            self.video_state.update(
                {
                    "duration": duration,
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )

            # 异步广播通知
            asyncio.create_task(
                self.broadcast_notification(
                    "video_loaded", "视频已加载", video_path=self.video_state["current_video"], duration=duration
                )
            )

            return {"status": "success", "event": "loaded", "duration": duration}

        elif event_type == "ended":
            # 视频播放结束
            self.video_state.update(
                {
                    "status": "stopped",
                    "position": 0,
                    "last_update": datetime.datetime.now().isoformat(),
                }
            )

            # 异步广播通知
            asyncio.create_task(
                self.broadcast_notification("video_ended", "视频播放结束", video_path=self.video_state["current_video"])
            )

            return {"status": "success", "event": "ended"}

        elif event_type == "error":
            # 视频播放错误
            error_message = kwargs.get("error", "未知错误")

            # 异步广播通知
            asyncio.create_task(
                self.broadcast_notification(
                    "video_error",
                    f"视频播放错误: {error_message}",
                    video_path=self.video_state["current_video"],
                    error=error_message,
                )
            )

            return {"status": "error", "event": "error", "message": error_message}

        else:
            self.logger.warning(f"未知的视频事件: {event_type}")
            return {"status": "error", "message": f"未知的视频事件: {event_type}"}
