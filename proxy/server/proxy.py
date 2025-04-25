"""
@Project ：Titan
@File    ：proxy.py
@Author  ：PySuper
@Date    ：2025/4/25 13:53
@Desc    ：Titan proxy.py
"""

"""
@Project ：Backend
@File    ：face_proxy.py
@Author  ：PySuper
@Date    ：2025/4/23 11:33
@Desc    ：Backend face_proxy.py
"""

import asyncio
import datetime
import json
import os
import subprocess
import threading
import uuid

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
from loguru import logger

from proxy.client.request import parse_ai as local_algorithm

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

logger.info("Face Proxy Start...")


def close_port(port):
    """关闭指定端口号的进程"""
    try:
        # Windows系统
        if os.name == "nt":
            try:
                result = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
                if result.strip():
                    for line in result.strip().split("\n"):
                        pid = line.strip().split()[-1]
                        subprocess.call(f"taskkill /PID {pid} /F", shell=True)
                else:
                    logger.info(f"端口 {port} 没有找到相关进程")
            except subprocess.CalledProcessError:
                logger.info(f"端口 {port} 没有找到相关进程")
        # Linux系统
        else:
            try:
                result = subprocess.check_output(f"lsof -i :{port}", shell=True).decode()
                if result.strip():
                    for line in result.strip().split("\n")[1:]:
                        pid = line.split()[1]
                        subprocess.call(f"kill -9 {pid}", shell=True)
                else:
                    logger.info(f"端口 {port} 没有找到相关进程")
            except subprocess.CalledProcessError:
                logger.info(f"端口 {port} 没有找到相关进程")
    except Exception as e:
        logger.error(f"关闭端口 {port} 时发生未知错误: {e}")


class FaceProxy(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_headers()

    # 设置跨域的具体方法
    def set_default_headers(self):
        super().set_default_headers()
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("X-XSS-Protection", "1")
        self.set_header("Content-Security-Policy", "default-src * 'self' 'unsafe-inline' 'unsafe-eval' data: blob:")
        self.set_header("Access-Control-Allow-Credentials", "true")
        request_headers = self.request.headers.get("Access-Control-Request-Headers", "")
        allowed_headers = "Content-Type, Content-Length, Authorization, Accept, X-Requested-With, X-File-Name, Cache-Control, devicetype"
        if request_headers:
            allowed_headers = f"{allowed_headers}, {request_headers}"
        self.set_header("Access-Control-Allow-Headers", allowed_headers)
        origin = self.request.headers.get("Origin", "*")
        self.set_header("Access-Control-Allow-Origin", origin)
        if self.request.method == "OPTIONS":
            self.set_header("Content-Type", "text/plain")
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

    def options(self):
        self.set_status(200)
        self.finish()

    def put(self):
        try:
            video_files = self.request.files.get("video", [])

            if not video_files:
                self.set_status(400)
                self.write({"status": "error", "message": "没有找到上传的视频文件"})
                return

            saved_files = []
            for video_file in video_files:
                original_filename = video_file["filename"]
                file_content = video_file["body"]
                content_type = video_file["content_type"]

                # 生成唯一文件名，保存文件
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{str(uuid.uuid4())[:8]}_{original_filename}"
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(file_content)

                # 记录文件信息
                file_info = {
                    "original_name": original_filename,
                    "saved_name": filename,
                    "file_path": file_path,
                    "file_size": len(file_content),
                    "content_type": content_type,
                }
                saved_files.append(file_info)
                logger.info(f"视频文件已保存: {file_path}")

                # 在后台线程中处理算法调用，避免阻塞主线程
                thread = threading.Thread(target=local_algorithm, args=(file_path,))
                thread.daemon = True
                thread.start()
                logger.info(f"已启动后台线程处理算法调用: {file_path}")

            response_data = {
                "status": "success",
                "message": f"成功上传 {len(saved_files)} 个视频文件",
                "files": saved_files,
            }
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")
            if ws_handler:
                ws_handler.send_message(json.dumps(response_data, ensure_ascii=False))
            self.write(response_data)
            self.finish()
        except Exception as e:
            self.set_status(500)
            self.write({"status": "error", "message": f"处理文件上传时出错: {str(e)}"})

    def post(self):
        """
        接收请求参数，处理video_path和result_path
        :return:
        """
        try:
            fps = 5  # 帧率，固定为5fps
            interval = 0.2  # 发送间隔，固定为0.2秒(200ms)
            logger.info(f"FPS: {fps}(固定), 间隔: {interval}秒(固定)")

            # 获取请求参数
            try:
                request_data = json.loads(self.request.body)
            except json.JSONDecodeError:
                request_data = {}
                logger.warning(f"无法解析请求体为JSON，尝试从form数据获取参数")

            # 尝试从不同来源获取参数
            video_path = request_data.get("video_path") if isinstance(request_data, dict) else None
            if not video_path:
                video_path = self.get_argument("video_path", None)

            result_path = request_data.get("result_path") if isinstance(request_data, dict) else None
            if not result_path:
                result_path = self.get_argument("result_path", None)

            logger.info(f"接收到参数 - video_path: {video_path}, result_path: {result_path}")

            # 获取WebSocket连接
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")

            if not ws_handler:
                logger.warning("没有活跃的WebSocket连接，无法转发数据")
                self.write({"status": "warning", "message": "没有活跃的客户端连接"})
                self.finish()
                return

            logger.info(f"找到活跃的WebSocket连接: {ws_handler.client_id}")

            # 处理video_path
            if video_path:
                logger.info(f"收到视频路径: {video_path}")

                # 记录并发送视频路径
                ws_handler.current_video_path = video_path
                ws_handler.send_message(
                    # json.dumps({"type": "video_path", "video_path": video_path}, ensure_ascii=False)
                    json.dumps(
                        {
                            "type": "video_path",
                            "video_path": "https://pysuper-blog-1.oss-cn-shanghai.aliyuncs.com/other/%E7%90%86%E6%83%B3.mp4",
                        },
                        ensure_ascii=False,
                    )
                )

                # 不再自动创建和启动视频流任务，只设置路径
                self.write({"status": "success", "message": "视频路径已设置并转发到客户端", "video_path": video_path})
                self.finish()
                return

            # 处理result_path
            if result_path:
                logger.info(f"收到结果路径: {result_path}")

                if not os.path.exists(result_path):
                    self.set_status(400)
                    self.write({"status": "error", "message": f"结果文件不存在: {result_path}"})
                    self.finish()
                    return

                # 处理结果文件
                try:
                    # 读取结果文件
                    with open(result_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)

                    # 获取数据
                    au_occ_list = result_data.get("au_occurrence", [])
                    au_int_list = result_data.get("au_intensity", [])
                    va_result_list = result_data.get("valence_arousal", [])
                    personality = result_data.get("personality", [])
                    depression = result_data.get("depression", "")

                    # 获取数据长度
                    data_length = (
                        min(len(au_occ_list), len(au_int_list), len(va_result_list))
                        if au_occ_list and au_int_list and va_result_list
                        else 0
                    )

                    if data_length == 0:
                        self.set_status(400)
                        self.write({"status": "error", "message": "结果文件中没有有效数据"})
                        self.finish()
                        return

                    # 创建任务处理结果
                    ws_handler.current_video_path = result_path  # 使用result_path作为标识符

                    # 创建任务但初始为暂停状态
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
                    self.finish()
                    return

                except Exception as e:
                    self.set_status(500)
                    self.write({"status": "error", "message": f"处理结果文件时出错: {str(e)}"})
                    self.finish()
                    return
            self.set_status(400)
            self.write({"status": "error", "message": "请提供video_path或result_path参数"})
            self.finish()
        except Exception as e:
            self.set_status(500)
            self.write({"status": "error", "message": f"处理请求时出错: {str(e)}"})
            self.finish()

    async def _send_result_data(self, ws_handler, result_data, fps=5):
        """
        按指定帧率发送结果数据

        :param ws_handler: WebSocket处理器
        :param result_data: 结果数据
        :param fps: 每秒帧数，默认5fps
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

            # 设置为暂停状态，等待播放命令
            ws_handler.is_paused = True  # 初始状态为暂停
            ws_handler.stop_tasks = False
            ws_handler.current_frame_index = 0

            # 储存结果数据供后续播放使用
            ws_handler.result_data = result_data

            # 通知客户端数据准备就绪，等待播放命令
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

    def get(self):
        """
        处理前端的播放请求和其他HTTP GET请求
        """
        try:
            action = self.get_argument("action", None)
            if not action:
                self.set_status(400)
                self.write({"status": "error", "message": "缺少action参数"})
                return

            # 获取WebSocket处理器
            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")

            if not ws_handler:
                self.set_status(400)
                self.write({"status": "error", "message": "没有活跃的WebSocket连接"})
                return

            # 根据action参数执行不同的操作
            if action == "play":
                if ws_handler.current_video_path:
                    # 如果已经有视频路径，则恢复播放
                    response = ws_handler.video_status(action="resume")
                    self.write(response)
                else:
                    # 如果没有视频路径，则返回错误
                    self.set_status(400)
                    self.write({"status": "error", "message": "没有可播放的视频"})
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
                # 重播视频
                if not ws_handler.current_video_path:
                    self.set_status(400)
                    self.write({"status": "error", "message": "没有可重播的视频"})
                    return

                fps = self.get_argument("fps", None)
                if fps:
                    fps = int(fps)

                # 停止当前任务并清除状态
                logger.info("通过control请求重播视频：停止所有当前发送任务并清除数据状态")
                ws_handler.stop_sending()

                try:
                    # 重置帧索引
                    ws_handler.current_frame_index = 0

                    # 启动新任务
                    task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
                    if task:
                        ws_handler.is_paused = False
                        self.write({"status": "success", "message": "视频已重新开始播放"})
                    else:
                        self.set_status(500)
                        self.write({"status": "error", "message": "启动视频重播失败"})
                except Exception as e:
                    self.set_status(500)
                    self.write({"status": "error", "message": f"重播视频时出错: {str(e)}"})
            else:
                self.set_status(400)
                self.write({"status": "error", "message": f"不支持的action: {action}"})
        except Exception as e:
            self.set_status(500)
            self.write({"status": "error", "message": f"处理请求时出错: {str(e)}"})

    def control(self):
        """
        控制视频的播放、暂停或停止
        """
        try:
            action = self.get_argument("action", None)
            if not action:
                self.set_status(400)
                self.write({"status": "error", "message": "缺少action参数"})
                return

            ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
            ws_handler = ws_handler_map.get("websocket_id")

            if not ws_handler:
                self.set_status(400)
                self.write({"status": "error", "message": "没有活跃的WebSocket连接"})
                return

            if action == "pause":
                response = ws_handler.video_status(action="pause")
                self.write(response)
            elif action == "resume" or action == "play":
                response = ws_handler.video_status(action="resume")
                self.write(response)
            elif action == "stop":
                ws_handler.stop_sending()
                self.write({"status": "success", "message": "视频已停止"})
            elif action == "replay":
                # 重播视频
                if not ws_handler.current_video_path:
                    self.set_status(400)
                    self.write({"status": "error", "message": "没有可重播的视频"})
                    return

                fps = self.get_argument("fps", None)
                if fps:
                    fps = int(fps)

                # 停止当前任务并清除状态
                logger.info("通过control请求重播视频：停止所有当前发送任务并清除数据状态")
                ws_handler.stop_sending()

                try:
                    # 重置帧索引
                    ws_handler.current_frame_index = 0

                    # 启动新任务
                    task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
                    if task:
                        ws_handler.is_paused = False
                        self.write({"status": "success", "message": "视频已重新开始播放"})
                    else:
                        self.set_status(500)
                        self.write({"status": "error", "message": "启动视频重播失败"})
                except Exception as e:
                    self.set_status(500)
                    self.write({"status": "error", "message": f"重播视频时出错: {str(e)}"})
            else:
                self.set_status(400)
                self.write({"status": "error", "message": f"不支持的action: {action}"})
        except Exception as e:
            self.set_status(500)
            self.write({"status": "error", "message": f"处理控制命令时出错: {str(e)}"})


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        if "ws_handlers" not in self.application.settings:
            self.application.settings["ws_handlers"] = []
        self.application.settings["ws_handlers"].append(self)
        self.frame_task = None
        self.stop_tasks = False
        # self.is_paused = False
        self.is_paused = True
        self.current_video_path = None
        self.current_frame_index = 0

    def check_origin(self, origin):
        return True

    def open(self):
        ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
        if ws_handler_map.get("websocket_id"):
            old_handler = ws_handler_map["websocket_id"]
            old_handler.stop_tasks = True
            if old_handler.frame_task and not old_handler.frame_task.done():
                old_handler.frame_task.cancel()
            old_handler.close()

        self.client_id = str(uuid.uuid4())
        ws_handler_map["websocket_id"] = self
        self.stop_tasks = False
        logger.info(f"WebSocket已连接，客户端ID: {self.client_id}")

    def send_message(self, message):
        """发送消息到WebSocket客户端"""
        try:
            if not self.ws_connection:
                logger.warning("尝试发送消息，但WebSocket连接已关闭")
                return False
            self.write_message(message)
            return True
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False

    def on_message(self, message):
        """处理从客户端接收的消息"""
        try:
            data = tornado.escape.json_decode(message)
            logger.info(f"收到客户端消息: {data}")
            if "action" in data:
                action = data["action"]
                if action == "play_video":  # 播放视频
                    if not self.current_video_path and "video_path" in data:
                        # 如果没有设置视频路径但客户端发送了路径，则设置
                        self.current_video_path = data["video_path"]
                        logger.info(f"从客户端设置视频路径: {self.current_video_path}")

                    if not self.current_video_path:
                        self.write_message(
                            json.dumps({"status": "error", "message": "暂无视频路径"}, ensure_ascii=False)
                        )
                        return

                    # 检查是否已有结果数据等待播放
                    if hasattr(self, "result_data") and self.result_data:

                        # 页面播放视频延迟问题
                        # if hasattr(self, "result_data") and self.result_data and data["time_"] > 0.001:
                        logger.info(f"开始播放已准备的结果数据")
                        # 启动发送结果数据的任务
                        fps = data.get("fps", 5)  # 默认5fps
                        loop = tornado.ioloop.IOLoop.current().asyncio_loop
                        self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
                        self.is_paused = False
                        self.write_message(
                            json.dumps(
                                {
                                    "status": "success",
                                    "message": "开始播放结果数据",
                                    "video_path": self.current_video_path,
                                },
                                ensure_ascii=False,
                            )
                        )
                        return

                    # 如果只有视频路径但没有结果数据，则通知前端需要提供结果数据
                    if self.current_video_path and not hasattr(self, "result_data"):
                        logger.info(f"只有视频路径但没有结果数据: {self.current_video_path}")
                        self.write_message(
                            json.dumps(
                                {
                                    "status": "warning",
                                    "message": "缺少结果数据，请先提供结果数据路径",
                                    "video_path": self.current_video_path,
                                },
                                ensure_ascii=False,
                            )
                        )
                        return

                    # 原代码中处理其他case的逻辑保持不变
                    # 如果有视频路径但没有任务，创建新任务
                    if not self.frame_task or self.frame_task.done():
                        try:
                            logger.info(f"启动播放任务: {self.current_video_path}")
                            task = self.start_video_streaming(self.current_video_path)
                            if task:
                                # 设置为不暂停，开始播放
                                self.is_paused = False
                                self.write_message(
                                    json.dumps(
                                        {
                                            "status": "success",
                                            "message": "开始播放数据",
                                            "video_path": self.current_video_path,
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                                return
                            else:
                                self.write_message(
                                    json.dumps({"status": "error", "message": "启动播放任务失败"}, ensure_ascii=False)
                                )
                                return
                        except Exception as e:
                            self.write_message(
                                json.dumps(
                                    {"status": "error", "message": f"启动播放任务时出错: {str(e)}"}, ensure_ascii=False
                                )
                            )
                            return

                    # 如果已有任务，则恢复播放
                    response = self.video_status(action="resume")
                    self.write_message(json.dumps(response, ensure_ascii=False))
                    return
                elif action == "pause_video":  # 暂停视频
                    response = self.video_status(action="pause")
                    self.write_message(json.dumps(response, ensure_ascii=False))
                    return
                elif action == "resume_video":  # 恢复视频
                    # 检查是否有任务运行
                    if not self.frame_task or self.frame_task.done():
                        if not self.current_video_path:
                            self.write_message(
                                json.dumps({"status": "error", "message": "暂无恢复视频"}, ensure_ascii=False)
                            )
                            return

                        # 检查是否已有结果数据等待播放
                        if hasattr(self, "result_data") and self.result_data:
                            logger.info(f"恢复播放准备的结果数据")
                            # 启动发送结果数据的任务
                            fps = data.get("fps", 5)  # 默认5fps
                            loop = tornado.ioloop.IOLoop.current().asyncio_loop
                            self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
                            self.is_paused = False
                            self.write_message(
                                json.dumps(
                                    {
                                        "status": "success",
                                        "message": "恢复播放结果数据",
                                        "video_path": self.current_video_path,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                            return

                        # 如果只有视频路径但没有结果数据，通知前端需要提供结果数据
                        if self.current_video_path and not hasattr(self, "result_data"):
                            logger.info(f"尝试恢复播放，但缺少结果数据: {self.current_video_path}")
                            self.write_message(
                                json.dumps(
                                    {
                                        "status": "warning",
                                        "message": "缺少结果数据，请先提供结果数据路径",
                                        "video_path": self.current_video_path,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                            return

                        # 其余情况保持不变
                        try:
                            logger.info(f"恢复播放时创建新任务: {self.current_video_path}")
                            task = self.start_video_streaming(self.current_video_path)
                            if task:
                                # 设置为不暂停，开始播放
                                self.is_paused = False
                                self.write_message(
                                    json.dumps(
                                        {
                                            "status": "success",
                                            "message": "开始播放数据",
                                            "video_path": self.current_video_path,
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                                return
                            else:
                                self.write_message(
                                    json.dumps({"status": "error", "message": "启动播放任务失败"}, ensure_ascii=False)
                                )
                                return
                        except Exception as e:
                            self.write_message(
                                json.dumps(
                                    {"status": "error", "message": f"启动播放任务时出错: {str(e)}"}, ensure_ascii=False
                                )
                            )
                            return

                    # 有正在运行的任务，恢复播放
                    response = self.video_status(action="resume")
                    self.write_message(json.dumps(response, ensure_ascii=False))
                    return
                elif action == "stop_video":  # 停止视频
                    self.stop_sending()
                    response = {"status": "success", "message": "数据播放已停止"}
                    self.write_message(json.dumps(response, ensure_ascii=False))
                    return
                elif action == "replay_video":  # 重播视频
                    if not self.current_video_path:
                        self.write_message(
                            json.dumps({"status": "error", "message": "没有可重播的视频"}, ensure_ascii=False)
                        )
                        return

                    # 首先停止当前所有发送任务和清除相关数据状态
                    logger.info("重播视频：停止所有当前发送任务并清除数据状态")
                    self.stop_sending()

                    # 重置相关数据状态
                    if hasattr(self, "curve_y1"):
                        self.curve_y1 = []
                    if hasattr(self, "curve_y2"):
                        self.curve_y2 = []

                    # 重置当前帧索引
                    self.current_frame_index = 0

                    # 检查是否有结果数据
                    if hasattr(self, "result_data") and self.result_data:
                        fps = data.get("fps", 5)  # 默认5fps
                        try:
                            logger.info("重新启动结果数据播放任务")
                            loop = tornado.ioloop.IOLoop.current().asyncio_loop
                            self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
                            self.is_paused = False
                            response = {"status": "success", "message": "结果数据已重新开始播放"}
                            self.write_message(json.dumps(response, ensure_ascii=False))
                            return
                        except Exception as e:
                            self.write_message(
                                json.dumps(
                                    {"status": "error", "message": f"重播结果数据时出错: {str(e)}"}, ensure_ascii=False
                                )
                            )
                            return

                    # 如果只有视频路径但没有结果数据，通知前端需要提供结果数据
                    if self.current_video_path and not hasattr(self, "result_data"):
                        logger.info(f"尝试重播视频，但缺少结果数据: {self.current_video_path}")
                        self.write_message(
                            json.dumps(
                                {
                                    "status": "warning",
                                    "message": "缺少结果数据，请先提供结果数据路径",
                                    "video_path": self.current_video_path,
                                },
                                ensure_ascii=False,
                            )
                        )
                        return

                    # 重新启动视频流任务
                    fps = data.get("fps", None)
                    try:
                        logger.info("重新启动视频流任务")
                        task = self.start_video_streaming(self.current_video_path, fps)
                        if task:
                            # 立即开始播放，不等待play命令
                            self.is_paused = False
                            response = {"status": "success", "message": "数据播放已重新开始"}
                        else:
                            response = {"status": "error", "message": "启动重播任务失败"}
                        self.write_message(json.dumps(response, ensure_ascii=False))
                    except Exception as e:
                        self.write_message(
                            json.dumps({"status": "error", "message": f"重播数据时出错: {str(e)}"}, ensure_ascii=False)
                        )
                    return
                elif action == "set_video_path":  # 设置视频路径
                    if "video_path" in data:
                        self.current_video_path = data["video_path"]
                        logger.info(f"设置视频路径: {self.current_video_path}")
                        self.write_message(
                            json.dumps(
                                {
                                    "status": "success",
                                    "message": "视频路径已设置",
                                    "video_path": self.current_video_path,
                                },
                                ensure_ascii=False,
                            )
                        )
                    else:
                        self.write_message(
                            json.dumps({"status": "error", "message": "缺少video_path参数"}, ensure_ascii=False)
                        )
                    return
                else:
                    logger.warning(f"未知的视频控制命令: {action}")
            self.write_message(json.dumps({"status": "received", "message": "消息已收到"}, ensure_ascii=False))
        except json.JSONDecodeError:
            self.write_message(json.dumps({"status": "error", "message": "无效的JSON格式"}, ensure_ascii=False))
        except Exception as e:
            self.write_message(
                json.dumps({"status": "error", "message": f"处理消息时出错: {str(e)}"}, ensure_ascii=False)
            )

    async def _play_result_data(self, fps=5):
        """
        发送结果数据的具体逻辑，只有在收到播放命令后才执行

        :param fps: 发送帧率，默认5fps
        """
        if not hasattr(self, "result_data") or not self.result_data:
            logger.error("没有可用的结果数据")
            await self._safe_write_message(
                json.dumps({"type": "error", "message": "没有可用的结果数据"}, ensure_ascii=False)
            )
            return

        try:
            # 获取数据
            result_data = self.result_data
            au_occ_list = result_data.get("au_occurrence", [])
            au_int_list = result_data.get("au_intensity", [])
            va_result_list = result_data.get("valence_arousal", [])
            personality = result_data.get("personality", [])
            depression = result_data.get("depression", [])
            expression = result_data.get("expression", [])
            global_blendshape = result_data.get("global_blendshape", [])

            # 获取数据长度
            data_length = (
                min(len(au_occ_list), len(au_int_list), len(va_result_list))
                if au_occ_list and au_int_list and va_result_list
                else 0
            )

            if data_length == 0:
                error_message = {"type": "error", "message": "结果数据为空，无法发送"}
                await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
                return

            # 计算发送间隔
            frame_delay = 1.0 / fps  # 0.2秒每帧
            logger.info(f"开始发送结果数据: 总帧数 {data_length}, FPS {fps}, 每帧间隔 {frame_delay}秒")

            # 设置数据间隔
            frame_step = 6  # 每6个值取一个
            sample_indices = list(range(0, data_length, frame_step))
            sample_length = len(sample_indices)
            logger.info(f"设置数据采样间隔: 每{frame_step}帧取一帧，采样后总帧数: {sample_length}")

            # 通知开始播放
            start_message = {
                "type": "status_change",
                "status": "playing",
                "message": "开始播放结果数据",
                "total_frames": sample_length,  # 更新为采样后的长度
                "fps": fps,
                "step": frame_step,
            }
            await self._safe_write_message(json.dumps(start_message, ensure_ascii=False))

            # 设置播放状态
            self.stop_tasks = False
            self.is_paused = False
            start_sample_index = min(self.current_frame_index // frame_step, len(sample_indices) - 1)  # 转换为采样索引

            # 表情计数器，整个视频过程中的累计计数
            expression_counts = {
                "angry": 0,  # 生气 (5)
                "happy": 0,  # 开心 (1)
                "neutral": 0,  # 中性 (0)
                "disgust": 0,  # 恶心 (6)
                "surprise": 0,  # 惊喜 (3)
                "contempt": 0,  # 蔑视 (7)
                "fear": 0,  # 害怕 (4)
                "sad": 0,  # 伤心 (2)
            }

            # 逐帧发送采样数据
            for sample_index in range(start_sample_index, sample_length):
                # 检查是否应该停止
                if self.stop_tasks:
                    logger.info("收到停止命令，终止结果发送")
                    break

                # 检查是否暂停
                if self.is_paused:
                    logger.info(f"结果发送暂停中，当前采样索引: {sample_index}")
                    while self.is_paused and not self.stop_tasks:
                        await asyncio.sleep(0.1)

                    if self.stop_tasks:
                        logger.info("暂停状态中收到停止命令，终止结果发送")
                        break

                    logger.info(f"结果发送已恢复，继续从采样索引 {sample_index} 开始")

                # 获取原始帧索引
                frame_index = sample_indices[sample_index]

                # 更新当前帧索引
                self.current_frame_index = frame_index

                # 创建当前帧的数据
                frame_data = {
                    "type": "frame_data",
                    "frame_index": sample_index,  # 采样后的索引
                    "original_index": frame_index,  # 原始索引
                    "total_frames": sample_length,  # 采样后的总帧数
                    "original_total": data_length,  # 原始总帧数
                    "timestamp": datetime.datetime.now().isoformat(),
                }

                # 添加固定值, 对personality中的值，乘以100，再取整
                frame_data["personality"] = [int(i * 100) for i in personality]
                frame_data["depression"] = depression

                # 添加表情数据, 累计表情类型出现次数
                if frame_index < len(expression):
                    try:
                        # 获取当前帧的表情值并转为整数
                        expr_value = int(expression[frame_index])

                        # 更新表情计数器
                        if expr_value == 0:
                            expression_counts["neutral"] += 1
                        elif expr_value == 1:
                            expression_counts["happy"] += 1
                        elif expr_value == 2:
                            expression_counts["sad"] += 1
                        elif expr_value == 3:
                            expression_counts["surprise"] += 1
                        elif expr_value == 4:
                            expression_counts["fear"] += 1
                        elif expr_value == 5:
                            expression_counts["angry"] += 1
                        elif expr_value == 6:
                            expression_counts["disgust"] += 1
                        elif expr_value == 7:
                            expression_counts["contempt"] += 1

                        # 添加符合指定格式的表情计数数组
                        frame_data["expression"] = [
                            {"name": "生气", "value": expression_counts["angry"]},
                            {"name": "开心", "value": expression_counts["happy"]},
                            {"name": "中性", "value": expression_counts["neutral"]},
                            {"name": "恶心", "value": expression_counts["disgust"]},
                            {"name": "惊讶", "value": expression_counts["surprise"]},
                            {"name": "蔑视", "value": expression_counts["contempt"]},
                            {"name": "害怕", "value": expression_counts["fear"]},
                            {"name": "伤心", "value": expression_counts["sad"]},
                        ]
                    except (ValueError, IndexError) as e:
                        logger.warning(f"处理表情数据时出错: {str(e)}")

                # 添加 global_blendshape
                if frame_index < len(global_blendshape):
                    # 修复数据类型问题
                    global_blendshape_labels = [
                        "中性",
                        "左眉下垂",
                        "右眉下垂",
                        "眉毛内侧上扬",
                        "左眉外侧上扬",
                        "右眉外侧上扬",
                        "鼓腮",
                        "左脸眯眼",
                        "右脸眯眼",
                        "左眼眨眼",
                        "右眼眨眼",
                        "左眼向下看",
                        "右眼向下看",
                        "左眼向内看",
                        "右眼向内看",
                        "左眼向外看",
                        "右眼向外看",
                        "左眼向上看",
                        "右眼向上看",
                        "左眼眯眼",
                        "右眼眯眼",
                        "左眼睁大",
                        "右眼睁大",
                        "下巴前伸",
                        "下巴左移",
                        "张嘴",
                        "下巴右移",
                        "闭嘴",
                        "左嘴角酒窝",
                        "右嘴角酒窝",
                        "左嘴角下撇",
                        "右嘴角下撇",
                        "嘴唇收拢",
                        "嘴向左偏",
                        "左下唇下压",
                        "右下唇下压",
                        "左嘴角用力",
                        "右嘴角用力",
                        "嘟嘴",
                        "嘴向右偏",
                        "下唇翻卷",
                        "上唇翻卷",
                        "下唇耸动",
                        "上唇耸动",
                        "左嘴角上扬",
                        "右嘴角上扬",
                        "左嘴角拉伸",
                        "右嘴角拉伸",
                        "左上唇抬起",
                        "右上唇抬起",
                        "左鼻翼皱起",
                        "右鼻翼皱起",
                    ]
                    global_blendshape_result = []
                    for i, value in enumerate(global_blendshape[frame_index]):
                        if i < len(global_blendshape_labels):
                            global_blendshape_result.append(
                                {"name": global_blendshape_labels[i], "value": "%.2f" % (value * 100)}
                            )
                        else:
                            global_blendshape_result.append(
                                {"name": f"global_blendshape_labels{i+1}", "value": "%.2f" % (value * 100)}
                            )
                    frame_data["global_blendshape"] = global_blendshape_result

                # 添加AU occurrence数据
                if frame_index < len(au_occ_list):
                    # 修复数据类型问题
                    au_labels = [
                        "内眉抬起",
                        "外眉抬起",
                        "眉毛皱起",
                        "上睑上升",
                        "脸颊提升",
                        "眼睑收紧",
                        "鼻子皱起",
                        "上唇抬起",
                        "拉动嘴角",
                        "收紧嘴角",
                        "嘴角向下",
                        "下唇向下",
                        "下唇抬起",
                        "收紧嘴唇",
                        "嘴唇按压",
                        "双唇分开",
                        "下巴下降",
                        "嘴巴张大",
                    ]
                    formatted_au = []
                    for i, value in enumerate(au_occ_list[frame_index]):
                        if i < len(au_labels):
                            formatted_au.append({"name": au_labels[i], "value": int(value)})
                        else:
                            formatted_au.append({"name": f"AU{i+1}", "value": int(value)})
                    frame_data["au_occurrence"] = formatted_au

                # 添加AU intensity数据
                if frame_index < len(au_int_list):
                    # 同样格式化intensity数据
                    au_int_labels = [
                        "内眉抬起",
                        "外眉抬起",
                        "眉毛皱起",
                        "上睑上升",
                        "脸颊提升",
                        "鼻子皱起",
                        "上唇抬起",
                        "拉动嘴角",
                        "收紧嘴角",
                        "嘴角向下",
                        "下唇抬起",
                        "嘴角拉伸",
                        "双唇分开",
                        "下巴下降",
                    ]
                    formatted_int = []
                    for i, value in enumerate(au_int_list[frame_index]):
                        if i < len(au_int_labels):
                            formatted_int.append({"name": au_int_labels[i], "value": float(value)})
                        else:
                            formatted_int.append({"name": f"AU{i+1}强度", "value": float(value)})
                    frame_data["au_intensity"] = formatted_int

                # 添加VA结果数据
                if frame_index < len(va_result_list):
                    if isinstance(va_result_list[frame_index], list) and len(va_result_list[frame_index]) >= 2:
                        frame_data["valence_arousal"] = {
                            "valence": float(va_result_list[frame_index][0]),
                            "arousal": float(va_result_list[frame_index][1]),
                        }
                    else:
                        frame_data["valence_arousal"] = {"valence": 0.0, "arousal": 0.0}

                # 添加曲线图数据，将valence_arousal拆分为y1和y2递增数据
                if frame_index < len(va_result_list):
                    if isinstance(va_result_list[frame_index], list) and len(va_result_list[frame_index]) >= 2:
                        # 获取当前帧的valence和arousal值
                        current_valence = float(va_result_list[frame_index][0])
                        current_arousal = float(va_result_list[frame_index][1])

                        # 初始化曲线数据
                        if not hasattr(self, "curve_y1"):
                            self.curve_y1 = []
                        if not hasattr(self, "curve_y2"):
                            self.curve_y2 = []

                        # 添加当前值到递增数组
                        self.curve_y1.append(current_valence)
                        self.curve_y2.append(current_arousal)

                        # 将递增数据添加到frame_data
                        frame_data["curve_data"] = {
                            "y1": self.curve_y1.copy(),  # valence的递增数据
                            "y2": self.curve_y2.copy(),  # arousal的递增数据
                        }
                    else:
                        # 如果没有有效的VA数据，初始化空数组
                        if not hasattr(self, "curve_y1"):
                            self.curve_y1 = []
                        if not hasattr(self, "curve_y2"):
                            self.curve_y2 = []

                        frame_data["curve_data"] = {"y1": self.curve_y1.copy(), "y2": self.curve_y2.copy()}

                await self._safe_write_message(json.dumps(frame_data, ensure_ascii=False))
                if sample_index % 10 == 0:
                    logger.info(
                        f"结果发送进度: {sample_index}/{sample_length} 帧 ({round(sample_index/sample_length*100, 1)}%)"
                    )
                await asyncio.sleep(frame_delay)

            # 发送完成消息
            if not self.stop_tasks:
                complete_message = {"type": "complete", "message": f"结果数据发送完成，共 {sample_length} 帧"}
                await self._safe_write_message(json.dumps(complete_message, ensure_ascii=False))
                logger.info(f"结果数据发送完成，共 {sample_length} 帧")

        except Exception as e:
            error_msg = f"发送结果数据时出错: {str(e)}"
            logger.error(error_msg)
            error_message = {"type": "error", "message": error_msg}
            await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))

    def stop_sending(self):
        """停止所有数据发送任务并清除相关状态"""
        logger.info("停止所有数据发送任务")
        # 设置停止标志并取消任务
        self.stop_tasks = True
        if self.frame_task and not self.frame_task.done():
            self.frame_task.cancel()

        # 重置曲线数据
        if hasattr(self, "curve_y1"):
            self.curve_y1 = []
        if hasattr(self, "curve_y2"):
            self.curve_y2 = []

        # 通知客户端任务已停止
        status_notification = {
            "type": "status_change",
            "status": "stopped",
            "message": "数据发送已停止",
            "timestamp": datetime.datetime.now().isoformat(),
        }
        asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))

        logger.info("已停止所有发送任务并清除相关状态")

    def on_close(self):
        self.stop_sending()
        ws_handler_map = self.application.settings.get("ws_handler_map", {})
        ws_handler_map.pop("websocket_id", None)
        logger.info(f"WebSocket已关闭，客户端ID: {self.client_id}")

    def video_status(self, action):
        """
        控制数据播放的暂停和恢复

        :param action: 控制动作，可选值："pause"暂停播放，"resume"恢复播放
        :return: 处理结果
        """
        logger.info(f"收到控制命令: {action}")

        if action == "pause":
            if not self.frame_task or self.frame_task.done():
                logger.warning("尝试暂停播放，但没有正在播放的任务")
                return {"status": "error", "message": "没有正在播放的数据"}

            if self.is_paused:
                logger.info("播放已经处于暂停状态")
                return {"status": "warning", "message": "播放已经处于暂停状态"}

            self.is_paused = True
            status_notification = {
                "type": "status_change",
                "status": "paused",
                "current_frame": self.current_frame_index,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
            logger.info(f"播放已暂停，当前帧: {self.current_frame_index}")
            return {
                "status": "success",
                "message": "播放已暂停",
                "action": "paused",
                "current_frame": self.current_frame_index,
            }

        elif action == "resume":
            if not self.frame_task or self.frame_task.done():
                logger.warning("尝试恢复播放，但没有可用的任务")
                if self.current_video_path:
                    return {"status": "info", "message": "需要先启动播放任务", "action": "need_start"}
                else:
                    return {"status": "error", "message": "没有可播放的数据"}

            if not self.is_paused:
                logger.info("播放已经在进行中")
                return {"status": "warning", "message": "播放已经在进行中"}

            # 取消暂停标志
            self.is_paused = False
            status_notification = {
                "type": "status_change",
                "status": "resumed",
                "current_frame": self.current_frame_index,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
            logger.info(f"播放已恢复，从帧 {self.current_frame_index} 开始")
            return {
                "status": "success",
                "message": "播放已恢复",
                "action": "resumed",
                "current_frame": self.current_frame_index,
            }

        else:
            logger.warning(f"不支持的控制动作: {action}")
            return {"status": "error", "message": f"不支持的动作: {action}"}

    def start_video_streaming(self, video_path, fps=None):
        """
        启动视频流发送任务

        :param video_path: 视频文件路径
        :param fps: 指定发送帧率，如果为None则使用视频原始帧率
        """
        logger.info(f"start_stream: {video_path}")
        if not self.ws_connection:
            return None

        # 检查视频文件
        if not os.path.exists(video_path):
            return None

        # 停止现有任务（如果有）
        if self.frame_task and not self.frame_task.done():
            logger.info("停止已存在的任务")
            self.stop_tasks = True
            self.frame_task.cancel()

        # 重置状态
        self.stop_tasks = False
        self.is_paused = True  # 初始化为暂停状态，等待前端播放请求
        self.current_frame_index = 0
        self.current_video_path = video_path

        try:
            loop = tornado.ioloop.IOLoop.current().asyncio_loop
            task = asyncio.ensure_future(self.send_video_stream(video_path, fps), loop=loop)
            logger.info(f"成功创建视频流发送任务: {task}")
            self.frame_task = task

            # 告知客户端任务已创建，等待播放命令
            status_notification = {
                "type": "status_change",
                "status": "ready",
                "message": "数据准备就绪，等待播放命令",
                "video_path": video_path,
            }
            asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))

            return task
        except Exception as e:
            logger.error(f"创建视频流发送任务时出错: {str(e)}")
            return None

    async def send_video_stream(self, video_path, fps=None):
        """
        处理视频控制，只发送结果数据而不发送视频数据

        :param video_path: 视频文件路径，仅用于查找对应的结果文件
        :param fps: 指定帧率，默认使用5fps
        """
        logger.info(f"处理视频路径: {video_path}")

        try:
            # 设置当前视频路径
            self.current_video_path = video_path

            # 固定设置为5fps
            send_fps = 5
            frame_delay = 1.0 / send_fps  # 0.2秒每帧

            # 尝试获取结果数据路径
            video_dir = os.path.dirname(video_path)
            video_base_name = os.path.splitext(os.path.basename(video_path))[0]
            possible_result_paths = [
                os.path.join(video_dir, f"{video_base_name}.json"),  # 同名json
                os.path.join(video_dir, "result.json"),  # 固定名称
                os.path.join(os.path.dirname(__file__), "result.json"),  # 当前目录下的result.json
            ]

            result_path = None
            for path in possible_result_paths:
                if os.path.exists(path):
                    result_path = path
                    logger.info(f"找到结果文件: {result_path}")
                    break

            if not result_path:
                logger.error("未找到有效的结果文件")
                error_message = {"type": "error", "message": "未找到有效的结果文件"}
                await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
                return

            # 加载结果数据
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)

                # 获取数据
                au_occ_list = result_data.get("au_occurrence", [])
                au_int_list = result_data.get("au_intensity", [])
                va_result_list = result_data.get("valence_arousal", [])
                personality = result_data.get("personality", [])
                depression = result_data.get("depression", "")

                # 获取数据长度
                data_length = (
                    min(len(au_occ_list), len(au_int_list), len(va_result_list))
                    if au_occ_list and au_int_list and va_result_list
                    else 0
                )

                if data_length == 0:
                    logger.error(f"结果文件 {result_path} 中没有有效数据")
                    error_message = {"type": "error", "message": "结果文件中没有有效数据"}
                    await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
                    return

                # 发送结果文件信息
                file_info = {
                    "type": "result_info",
                    "result_path": result_path,
                    "data_length": data_length,
                    "fps": send_fps,
                    "frame_delay": frame_delay,
                    "video_path": video_path,
                }
                await self._safe_write_message(json.dumps(file_info, ensure_ascii=False))
                logger.info(f"开始发送结果数据: 总帧数 {data_length}, FPS {send_fps}, 每帧间隔 {frame_delay}秒")

                # 发送结果数据
                frame_index = 0
                self.current_frame_index = 0

                while frame_index < data_length and not self.stop_tasks:
                    # 检查暂停状态
                    if self.is_paused:
                        logger.info(f"数据发送暂停中，当前帧：{frame_index}")
                        # 当暂停时，循环等待直到恢复播放或停止
                        while self.is_paused and not self.stop_tasks:
                            # 每0.1秒检查一次状态
                            await asyncio.sleep(0.1)

                        # 如果循环是因为stop_tasks退出的，则跳出外层循环
                        if self.stop_tasks:
                            logger.info("暂停状态中收到停止命令，终止数据发送")
                            break

                        logger.info(f"数据发送已恢复，继续从帧 {frame_index} 开始")

                    # 构建当前帧的结果数据
                    frame_data = {
                        "type": "frame_data",
                        "frame_index": frame_index,
                        "total_frames": data_length,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }

                    # 添加AU occurrence数据
                    if frame_index < len(au_occ_list):
                        frame_data["au_occurrence"] = au_occ_list[frame_index]

                    # 添加AU intensity数据
                    if frame_index < len(au_int_list):
                        frame_data["au_intensity"] = au_int_list[frame_index]

                    # 添加VA结果数据
                    if frame_index < len(va_result_list):
                        frame_data["valence_arousal"] = va_result_list[frame_index]

                    # 发送数据
                    await self._safe_write_message(json.dumps(frame_data, ensure_ascii=False))

                    # 每50帧打印一次日志
                    if frame_index % 50 == 0:
                        logger.info(
                            f"数据发送进度: {frame_index}/{data_length} 帧 ({round(frame_index/data_length*100, 1)}%)"
                        )

                    # 更新帧索引
                    frame_index += 1
                    self.current_frame_index = frame_index

                    # 控制发送速度
                    await asyncio.sleep(frame_delay)

                # 发送完成消息
                if not self.stop_tasks:
                    complete_message = {"type": "complete", "message": f"数据发送完成，共 {data_length} 帧"}
                    await self._safe_write_message(json.dumps(complete_message, ensure_ascii=False))
                    logger.info(f"数据发送完成，共 {data_length} 帧")

            except Exception as e:
                error_msg = f"处理结果文件时出错: {str(e)}"
                logger.error(error_msg)
                error_message = {"type": "error", "message": error_msg}
                await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))

        except Exception as e:
            logger.error(f"处理数据时出错: {str(e)}")
            if self.ws_connection:
                error_message = {"type": "error", "message": f"处理数据时出错: {str(e)}"}
                await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))

    async def _safe_write_message(self, message):
        """安全地发送WebSocket消息，处理可能的异常"""
        if not self.ws_connection:
            logger.warning("尝试发送消息，但WebSocket连接已关闭")
            return False
        try:
            await self.write_message(message)
            return True
        except Exception as e:
            logger.error(f"发送WebSocket消息时出错: {str(e)}")
            return False


def make_app():
    return tornado.web.Application(
        [
            (r"/upload", FaceProxy),
            (r"/websocket", WebSocketHandler),
            (r"/control", FaceProxy),
            (r"/video_control", FaceProxy),  # 新增路由，用于处理GET请求的视频控制
        ],
    )


def run(http_port=9000, ws_port=9001):
    close_port(http_port)
    close_port(ws_port)
    try:
        app = make_app()
        server = tornado.httpserver.HTTPServer(app)
        server.listen(http_port, address="0.0.0.0")
        ws_server = tornado.httpserver.HTTPServer(app)
        ws_server.add_sockets(tornado.netutil.bind_sockets(ws_port))
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
