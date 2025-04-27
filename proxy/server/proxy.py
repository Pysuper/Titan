"""
@Project ：Titan
@File    ：proxy.py
@Author  ：PySuper
@Date    ：2025/4/25 13:53
@Desc    ：Titan proxy.py
"""

import asyncio
import datetime
import json
import os
import uuid

import tornado.web
import tornado.websocket
from loguru import logger

from proxy.config.files import UPLOAD_DIR


class FaceProxy(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_headers()

    def set_default_headers(self):
        """设置跨域和安全相关的HTTP响应头"""
        super().set_default_headers()

        # 跨域相关设置
        origin = self.request.headers.get("Origin", "*")
        self.set_header("Access-Control-Allow-Origin", origin)
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Credentials", "true")

        # 合并请求头
        default_headers = "Content-Type, Content-Length, Authorization, Accept, X-Requested-With, X-File-Name, Cache-Control, devicetype"
        request_headers = self.request.headers.get("Access-Control-Request-Headers", "")
        allowed_headers = default_headers + (f", {request_headers}" if request_headers else "")
        self.set_header("Access-Control-Allow-Headers", allowed_headers)

        # 安全相关设置
        self.set_header("X-XSS-Protection", "1")
        self.set_header("Content-Security-Policy", "default-src * 'self' 'unsafe-inline' 'unsafe-eval' data: blob:")

        # 内容类型设置
        content_type = "text/plain" if self.request.method == "OPTIONS" else "application/json; charset=UTF-8"
        self.set_header("Content-Type", content_type)

    def options(self):
        self.set_status(200)
        self.finish()

    def get(self):
        """
        处理前端的播放请求和其他HTTP GET请求
        # 查询数据
        # 返回响应

        接收到http get请求后，向websocket发送请求
        """

        try:
            # 接受参数
            action = self.get_argument("action", None)

            # 数据校验
            if not action:
                self.handel_exception("缺少action参数")

            # 查询websocket客户端链连接状态
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")
            if not ws_handler:
                return self.handel_exception("没有活跃的WebSocket连接")

            # 根据请求参数执行不同的操作
            if action == "play":
                if ws_handler.current_video_path:
                    # 如果已经有视频路径，则恢复播放
                    response = ws_handler.video_status(action="resume")
                    self.write(response)
                else:
                    # 如果没有视频路径，则返回错误
                    self.handel_exception("没有可播放的视频")
            elif action == "pause":
                response = ws_handler.video_status(action="pause")
                self.write(response)
            elif action == "resume":
                response = ws_handler.video_status(action="resume")
                self.write(response)
            elif action == "stop":
                ws_handler.stop_sending()
                self.write({"status": "success", "message": "视频已停止"})
            elif action == "replay":
                if not ws_handler.current_video_path:
                    self.handel_exception("没有可播放的视频")
                fps = self.get_argument("fps", None)
                if fps:
                    fps = int(fps)

                # 停止当前任务并重新开始
                ws_handler.stop_sending()
                try:
                    task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
                    if task:
                        ws_handler.is_paused = False
                        self.write({"status": "success", "message": "视频已重新开始播放"})
                    else:
                        self.handel_exception("启动视频重播失败")
                except Exception as e:
                    self.handel_exception(f"重播视频时出错: {str(e)}")
            else:
                self.handel_exception("不支持的action: {action}")
        except Exception as e:
            self.handel_exception(f"处理请求时出错: {str(e)}")

    def handel_exception(self, msg):
        logger.error(msg)
        self.set_status(400)
        self.write({"status": "error", "message": msg})
        return

    def handel_ws_exception(self, msg):
        logger.error(msg)
        self.write({"status": "error", "message": msg})
        return

    def put(self):
        """处理视频文件上传请求"""
        try:
            video_files = self.request.files.get("video", [])
            if not video_files:
                self.handel_exception("没有找到上传的视频文件")

            saved_files = self._save_uploaded_files(video_files)
            response_data = {
                "status": "success",
                "message": f"成功上传 {len(saved_files)} 个视频文件",
                "files": saved_files,
            }
            self._notify_websocket_clients(response_data)
            self.write(response_data)

        except Exception as e:
            self.handel_exception(f"处理文件上传时出错: {str(e)}")

    def post(self):
        """
        接收请求参数，处理video_path和result_path
        :return: JSON响应
        """
        try:
            # 固定参数设置
            fps = 5  # 帧率，固定为5fps
            interval = 0.2  # 发送间隔，固定为0.2秒(200ms)
            logger.info(f"FPS: {fps}(固定), 间隔: {interval}秒(固定)")

            # 获取请求参数
            params = self._extract_request_parameters()
            video_path, result_path = params.get("video_path"), params.get("result_path")
            logger.info(f"接收到参数 - video_path: {video_path}, result_path: {result_path}")

            # 获取并验证WebSocket连接
            ws_handler = self._get_websocket_handler()
            if not ws_handler:
                self.handel_ws_exception("没有活跃的WebSocket连接")

            logger.info(f"找到活跃的WebSocket连接: {ws_handler.client_id}")
            if video_path:
                self._handle_video_path(ws_handler, video_path)
            elif result_path:
                self._handle_result_path(ws_handler, result_path, fps)
            else:
                self.handel_exception("请提供video_path或result_path参数")
        except Exception as e:
            self.handel_exception(f"处理请求时出错: {str(e)}")

    def control(self):
        """
        控制视频的播放、暂停或停止

        支持的操作:
        - pause: 暂停视频播放
        - resume/play: 恢复/开始视频播放
        - stop: 停止视频播放
        - replay: 重新播放视频

        返回:
        - JSON响应，包含状态和消息
        """
        try:
            action = self.get_argument("action", None)
            if not action:
                self.handel_exception("缺少action参数")

            ws_handler = self._get_websocket_handler()
            if not ws_handler:
                return self.handel_exception("没有活跃的WebSocket连接")

            if action == "pause":
                response = ws_handler.video_status(action="pause")
                self.write(response)
            elif action in ["resume", "play"]:
                response = ws_handler.video_status(action="resume")
                self.write(response)
            elif action == "stop":
                ws_handler.stop_sending()
                self.write({"status": "success", "message": "视频已停止"})
            elif action == "replay":
                self._handle_replay_action(ws_handler)
            else:
                self.handel_exception(f"不支持的action: {action}")
        except Exception as e:
            self.handel_exception(f"处理控制命令时出错: {str(e)}")

    def _get_websocket_handler(self):
        """获取WebSocket处理器"""
        ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
        return ws_handler_map.get("websocket_id")

    def _handle_replay_action(self, ws_handler):
        """处理重播操作"""
        if not ws_handler.current_video_path:
            self.handel_exception("没有可重播的视频")

        try:
            fps = self.get_argument("fps", None)
            if fps:
                fps = int(fps)
        except ValueError:
            self.handel_exception("fps参数不是一个整数")

        ws_handler.stop_sending()
        try:
            task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
            if task:
                ws_handler.is_paused = False
                self.write(
                    {
                        "status": "success",
                        "message": "视频已重新开始播放",
                        "video_path": ws_handler.current_video_path,
                        "fps": fps,
                    }
                )
            else:
                self.handel_exception("启动视频重播失败")
        except Exception as e:
            self.handel_exception(f"重播视频时出错: {str(e)}")

    def _save_uploaded_files(self, video_files):
        """保存上传的视频文件并返回文件信息列表"""
        saved_files = []

        for video_file in video_files:
            original_filename = video_file["filename"]
            file_content = video_file["body"]
            content_type = video_file["content_type"]

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
                }
                saved_files.append(file_info)
                logger.info(f"视频文件已保存: {file_path}")
            except IOError as e:
                logger.error(f"保存文件 {original_filename} 时出错: {str(e)}")

        return saved_files

    def _notify_websocket_clients(self, data):
        """向WebSocket客户端发送通知"""
        try:
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")
            if ws_handler:
                if ws_handler.send_message(json.dumps(data, ensure_ascii=False)):
                    logger.debug("成功通知WebSocket客户端上传结果")
                else:
                    logger.warning("通知WebSocket客户端失败")
        except Exception as e:
            logger.error(f"通知WebSocket客户端时出错: {str(e)}")

    def _extract_request_parameters(self):
        """提取请求参数，支持JSON和表单数据"""
        params = {}

        # 尝试解析JSON请求体
        try:
            request_data = json.loads(self.request.body)
            if isinstance(request_data, dict):
                params.update(request_data)
        except json.JSONDecodeError:
            logger.warning("无法解析请求体为JSON，尝试从form数据获取参数")

        # 尝试从URL参数获取
        for param in ["video_path", "result_path"]:
            if param not in params or not params[param]:
                value = self.get_argument(param, None)
                if value:
                    params[param] = value

        return params

    def _handle_video_path(self, ws_handler, video_path):
        """处理视频路径请求"""
        logger.info(f"处理视频路径: {video_path}")
        ws_handler.current_video_path = video_path
        ws_handler.send_message(json.dumps({"type": "video_path", "video_path": video_path}, ensure_ascii=False))

        # 创建任务但不自动开始播放
        if not ws_handler.frame_task or ws_handler.frame_task.done():
            task = ws_handler.start_video_streaming(video_path)
            if not task:
                self.handel_exception(f"创建数据发送任务失败: {video_path}")
        self.write({"status": "success", "message": "视频路径已设置并转发到客户端", "video_path": video_path})

    def _handle_result_path(self, ws_handler, result_path, fps):
        """处理结果文件路径请求"""
        logger.info(f"处理结果路径: {result_path}")

        # 验证文件存在
        if not os.path.exists(result_path):
            self.handel_exception(f"结果文件不存在: {result_path}")

        try:
            # 读取并验证结果数据
            result_data = self._read_result_file(result_path)
            if not result_data:
                self.handel_exception("无法读取或解析结果文件")

            # 验证数据有效性
            data_length = self._validate_result_data(result_data)
            if data_length == 0:
                self.handel_exception("结果文件中没有有效数据")

            # 创建任务处理结果
            ws_handler.current_video_path = result_path  # 使用result_path作为标识符
            asyncio.create_task(self._send_result_data(ws_handler, result_data, fps))

            self.write(
                {
                    "status": "success",
                    "message": f"结果处理任务已准备就绪，等待播放命令，将按{fps}fps的帧率发送结果",
                    "data_length": data_length,
                    "fps": fps,
                    "result_path": result_path,
                }
            )
        except Exception as e:
            self.handel_exception(f"处理结果文件时出错: {str(e)}")

    def _read_result_file(self, file_path):
        """读取结果文件并返回JSON数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"读取结果文件失败: {str(e)}")
            return None

    def _validate_result_data(self, result_data):
        """验证结果数据并返回有效数据长度"""
        # 获取关键数据列表
        au_occ_list = result_data.get("au_occurrence", [])
        au_int_list = result_data.get("au_intensity", [])
        va_result_list = result_data.get("valence_arousal", [])

        # 计算有效数据长度
        if au_occ_list and au_int_list and va_result_list:
            return min(len(au_occ_list), len(au_int_list), len(va_result_list))
        return 0

    async def _send_result_data(self, ws_handler, result_data, fps=5):
        """
        按指定帧率发送结果数据

        @param ws_handler: WebSocket处理器
        @param result_data: 结果数据
        @param fps: 每秒帧数，默认5fps
        """
        try:
            # 获取数据
            au_occ_list = result_data.get("au_occurrence", [])
            au_int_list = result_data.get("au_intensity", [])
            va_result_list = result_data.get("valence_arousal", [])

            # 获取数据长度
            data_length = (
                min(len(au_occ_list), len(au_int_list), len(va_result_list))
                if au_occ_list and au_int_list and va_result_list
                else 0
            )

            if data_length == 0:
                error_message = {"type": "error", "message": "结果数据为空，无法发送"}
                await ws_handler._safe_write_message(json.dumps(error_message, ensure_ascii=False))
                return

            # 计算发送间隔
            frame_delay = 1.0 / fps  # 0.2秒每帧
            logger.info(f"准备发送结果数据: 总帧数 {data_length}, FPS {fps}, 每帧间隔 {frame_delay}秒")

            # 发送初始信息
            init_message = {
                "type": "result_info",
                "total_frames": data_length,
                "fps": fps,
                "frame_delay": frame_delay,
            }
            await ws_handler._safe_write_message(json.dumps(init_message, ensure_ascii=False))

            ws_handler.is_paused = True  # 初始状态为暂停
            ws_handler.stop_tasks = False
            ws_handler.current_frame_index = 0
            ws_handler.result_data = result_data

            status_notification = {
                "type": "status_change",
                "status": "ready",
                "message": "结果数据准备就绪，等待播放命令",
                "total_frames": data_length,
            }
            await ws_handler._safe_write_message(json.dumps(status_notification, ensure_ascii=False))
            logger.info(f"结果数据已准备就绪，等待客户端发送播放命令")
            return

        except Exception as e:
            error_msg = f"处理结果数据时出错: {str(e)}"
            logger.error(error_msg)
            error_message = {"type": "error", "message": error_msg}
            await ws_handler._safe_write_message(json.dumps(error_message, ensure_ascii=False))
