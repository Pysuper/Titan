# """
# @Project ：Backend
# @File    ：face_proxy.py
# @Author  ：PySuper
# @Date    ：2025/4/23 11:33
# @Desc    ：Backend face_proxy.py
# """
#
# import asyncio
# import datetime
# import json
# import os
# import subprocess
# import uuid
#
# import tornado.escape
# import tornado.httpserver
# import tornado.ioloop
# import tornado.web
# import tornado.websocket
# from loguru import logger
#
# UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
# if not os.path.exists(UPLOAD_DIR):
#     os.makedirs(UPLOAD_DIR)
#
# logger.info("Face Proxy Start...")
#
# """
# {"action": "play_video"} // 开始播放
# {"action": "pause_video"} // 暂停播放
# {"action": "resume_video"} // 恢复播放
# {"action": "stop_video"} // 停止播放
# {"action": "replay_video"} // 重新播放
# """
#
#
# def close_port(port):
#     """关闭指定端口号的进程"""
#     try:
#         # Windows系统
#         if os.name == "nt":
#             try:
#                 result = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
#                 if result.strip():
#                     for line in result.strip().split("\n"):
#                         pid = line.strip().split()[-1]
#                         subprocess.call(f"taskkill /PID {pid} /F", shell=True)
#                 else:
#                     logger.info(f"端口 {port} 没有找到相关进程")
#             except subprocess.CalledProcessError:
#                 logger.info(f"端口 {port} 没有找到相关进程")
#         # Linux系统
#         else:
#             try:
#                 result = subprocess.check_output(f"lsof -i :{port}", shell=True).decode()
#                 if result.strip():
#                     for line in result.strip().split("\n")[1:]:
#                         pid = line.split()[1]
#                         subprocess.call(f"kill -9 {pid}", shell=True)
#                 else:
#                     logger.info(f"端口 {port} 没有找到相关进程")
#             except subprocess.CalledProcessError:
#                 logger.info(f"端口 {port} 没有找到相关进程")
#     except Exception as e:
#         logger.error(f"关闭端口 {port} 时发生未知错误: {e}")
#
#
# class FaceProxy(tornado.web.RequestHandler):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.set_default_headers()
#
#     def set_default_headers(self):
#         """设置跨域和安全相关的HTTP响应头"""
#         super().set_default_headers()
#
#         # 跨域相关设置
#         origin = self.request.headers.get("Origin", "*")
#         self.set_header("Access-Control-Allow-Origin", origin)
#         self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
#         self.set_header("Access-Control-Allow-Credentials", "true")
#
#         # 合并请求头
#         default_headers = "Content-Type, Content-Length, Authorization, Accept, X-Requested-With, X-File-Name, Cache-Control, devicetype"
#         request_headers = self.request.headers.get("Access-Control-Request-Headers", "")
#         allowed_headers = default_headers + (f", {request_headers}" if request_headers else "")
#         self.set_header("Access-Control-Allow-Headers", allowed_headers)
#
#         # 安全相关设置
#         self.set_header("X-XSS-Protection", "1")
#         self.set_header("Content-Security-Policy", "default-src * 'self' 'unsafe-inline' 'unsafe-eval' data: blob:")
#
#         # 内容类型设置
#         content_type = "text/plain" if self.request.method == "OPTIONS" else "application/json; charset=UTF-8"
#         self.set_header("Content-Type", content_type)
#
#     def options(self):
#         self.set_status(200)
#         self.finish()
#
#     def get(self):
#         """
#         处理前端的播放请求和其他HTTP GET请求
#         """
#         try:
#             action = self.get_argument("action", None)
#             if not action:
#                 self.handel_exception("缺少action参数")
#
#             # 获取WebSocket处理器
#             ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
#             ws_handler = ws_handler_map.get("websocket_id")
#             if not ws_handler:
#                 return self.handel_exception("没有活跃的WebSocket连接")
#
#             # 根据action参数执行不同的操作
#             if action == "play":
#                 if ws_handler.current_video_path:
#                     # 如果已经有视频路径，则恢复播放
#                     response = ws_handler.video_status(action="resume")
#                     self.write(response)
#                 else:
#                     # 如果没有视频路径，则返回错误
#                     self.handel_exception("没有可播放的视频")
#             elif action == "pause":
#                 response = ws_handler.video_status(action="pause")
#                 self.write(response)
#             elif action == "resume":
#                 response = ws_handler.video_status(action="resume")
#                 self.write(response)
#             elif action == "stop":
#                 ws_handler.stop_sending()
#                 self.write({"status": "success", "message": "视频已停止"})
#             elif action == "replay":
#                 if not ws_handler.current_video_path:
#                     self.handel_exception("没有可播放的视频")
#                 fps = self.get_argument("fps", None)
#                 if fps:
#                     fps = int(fps)
#
#                 # 停止当前任务并重新开始
#                 ws_handler.stop_sending()
#                 try:
#                     task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
#                     if task:
#                         ws_handler.is_paused = False
#                         self.write({"status": "success", "message": "视频已重新开始播放"})
#                     else:
#                         self.handel_exception("启动视频重播失败")
#                 except Exception as e:
#                     self.handel_exception(f"重播视频时出错: {str(e)}")
#             else:
#                 self.handel_exception("不支持的action: {action}")
#         except Exception as e:
#             self.handel_exception(f"处理请求时出错: {str(e)}")
#
#     def handel_exception(self, msg):
#         logger.error(msg)
#         self.set_status(400)
#         self.write({"status": "error", "message": msg})
#         return
#
#     def handel_ws_exception(self, msg):
#         logger.error(msg)
#         self.write({"status": "error", "message": msg})
#         return
#
#     def put(self):
#         """处理视频文件上传请求"""
#         try:
#             video_files = self.request.files.get("video", [])
#             if not video_files:
#                 self.handel_exception("没有找到上传的视频文件")
#
#             saved_files = self._save_uploaded_files(video_files)
#             response_data = {
#                 "status": "success",
#                 "message": f"成功上传 {len(saved_files)} 个视频文件",
#                 "files": saved_files,
#             }
#             self._notify_websocket_clients(response_data)
#             self.write(response_data)
#
#         except Exception as e:
#             self.handel_exception(f"处理文件上传时出错: {str(e)}")
#
#     def post(self):
#         """
#         接收请求参数，处理video_path和result_path
#         :return: JSON响应
#         """
#         try:
#             # 固定参数设置
#             fps = 5  # 帧率，固定为5fps
#             interval = 0.2  # 发送间隔，固定为0.2秒(200ms)
#             logger.info(f"FPS: {fps}(固定), 间隔: {interval}秒(固定)")
#
#             # 获取请求参数
#             params = self._extract_request_parameters()
#             video_path, result_path = params.get("video_path"), params.get("result_path")
#             logger.info(f"接收到参数 - video_path: {video_path}, result_path: {result_path}")
#
#             # 获取并验证WebSocket连接
#             ws_handler = self._get_websocket_handler()
#             if not ws_handler:
#                 self.handel_ws_exception("没有活跃的WebSocket连接")
#
#             logger.info(f"找到活跃的WebSocket连接: {ws_handler.client_id}")
#             if video_path:
#                 self._handle_video_path(ws_handler, video_path)
#             elif result_path:
#                 self._handle_result_path(ws_handler, result_path, fps)
#             else:
#                 self.handel_exception("请提供video_path或result_path参数")
#         except Exception as e:
#             self.handel_exception(f"处理请求时出错: {str(e)}")
#
#     def control(self):
#         """
#         控制视频的播放、暂停或停止
#
#         支持的操作:
#         - pause: 暂停视频播放
#         - resume/play: 恢复/开始视频播放
#         - stop: 停止视频播放
#         - replay: 重新播放视频
#
#         返回:
#         - JSON响应，包含状态和消息
#         """
#         try:
#             action = self.get_argument("action", None)
#             if not action:
#                 self.handel_exception("缺少action参数")
#
#             ws_handler = self._get_websocket_handler()
#             if not ws_handler:
#                 return self.handel_exception("没有活跃的WebSocket连接")
#
#             if action == "pause":
#                 response = ws_handler.video_status(action="pause")
#                 self.write(response)
#             elif action in ["resume", "play"]:
#                 response = ws_handler.video_status(action="resume")
#                 self.write(response)
#             elif action == "stop":
#                 ws_handler.stop_sending()
#                 self.write({"status": "success", "message": "视频已停止"})
#             elif action == "replay":
#                 self._handle_replay_action(ws_handler)
#             else:
#                 self.handel_exception(f"不支持的action: {action}")
#         except Exception as e:
#             self.handel_exception(f"处理控制命令时出错: {str(e)}")
#
#     def _get_websocket_handler(self):
#         """获取WebSocket处理器"""
#         ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
#         return ws_handler_map.get("websocket_id")
#
#     def _handle_replay_action(self, ws_handler):
#         """处理重播操作"""
#         if not ws_handler.current_video_path:
#             self.handel_exception("没有可重播的视频")
#
#         try:
#             fps = self.get_argument("fps", None)
#             if fps:
#                 fps = int(fps)
#         except ValueError:
#             self.handel_exception("fps参数不是一个整数")
#
#         ws_handler.stop_sending()
#         try:
#             task = ws_handler.start_video_streaming(ws_handler.current_video_path, fps)
#             if task:
#                 ws_handler.is_paused = False
#                 self.write(
#                     {
#                         "status": "success",
#                         "message": "视频已重新开始播放",
#                         "video_path": ws_handler.current_video_path,
#                         "fps": fps,
#                     }
#                 )
#             else:
#                 self.handel_exception("启动视频重播失败")
#         except Exception as e:
#             self.handel_exception(f"重播视频时出错: {str(e)}")
#
#     def _save_uploaded_files(self, video_files):
#         """保存上传的视频文件并返回文件信息列表"""
#         saved_files = []
#
#         for video_file in video_files:
#             original_filename = video_file["filename"]
#             file_content = video_file["body"]
#             content_type = video_file["content_type"]
#
#             timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#             unique_id = str(uuid.uuid4())[:8]
#             filename = f"{timestamp}_{unique_id}_{original_filename}"
#             file_path = os.path.join(UPLOAD_DIR, filename)
#
#             try:
#                 with open(file_path, "wb") as f:
#                     f.write(file_content)
#
#                 file_info = {
#                     "original_name": original_filename,
#                     "saved_name": filename,
#                     "file_path": file_path,
#                     "file_size": len(file_content),
#                     "content_type": content_type,
#                     "upload_time": timestamp,
#                 }
#                 saved_files.append(file_info)
#                 logger.info(f"视频文件已保存: {file_path}")
#             except IOError as e:
#                 logger.error(f"保存文件 {original_filename} 时出错: {str(e)}")
#
#         return saved_files
#
#     def _notify_websocket_clients(self, data):
#         """向WebSocket客户端发送通知"""
#         try:
#             ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
#             ws_handler = ws_handler_map.get("websocket_id")
#             if ws_handler:
#                 if ws_handler.send_message(json.dumps(data, ensure_ascii=False)):
#                     logger.debug("成功通知WebSocket客户端上传结果")
#                 else:
#                     logger.warning("通知WebSocket客户端失败")
#         except Exception as e:
#             logger.error(f"通知WebSocket客户端时出错: {str(e)}")
#
#     def _extract_request_parameters(self):
#         """提取请求参数，支持JSON和表单数据"""
#         params = {}
#
#         # 尝试解析JSON请求体
#         try:
#             request_data = json.loads(self.request.body)
#             if isinstance(request_data, dict):
#                 params.update(request_data)
#         except json.JSONDecodeError:
#             logger.warning("无法解析请求体为JSON，尝试从form数据获取参数")
#
#         # 尝试从URL参数获取
#         for param in ["video_path", "result_path"]:
#             if param not in params or not params[param]:
#                 value = self.get_argument(param, None)
#                 if value:
#                     params[param] = value
#
#         return params
#
#     def _handle_video_path(self, ws_handler, video_path):
#         """处理视频路径请求"""
#         logger.info(f"处理视频路径: {video_path}")
#         ws_handler.current_video_path = video_path
#         ws_handler.send_message(json.dumps({"type": "video_path", "video_path": video_path}, ensure_ascii=False))
#
#         # 创建任务但不自动开始播放
#         if not ws_handler.frame_task or ws_handler.frame_task.done():
#             task = ws_handler.start_video_streaming(video_path)
#             if not task:
#                 self.handel_exception(f"创建数据发送任务失败: {video_path}")
#         self.write({"status": "success", "message": "视频路径已设置并转发到客户端", "video_path": video_path})
#
#     def _handle_result_path(self, ws_handler, result_path, fps):
#         """处理结果文件路径请求"""
#         logger.info(f"处理结果路径: {result_path}")
#
#         # 验证文件存在
#         if not os.path.exists(result_path):
#             self.handel_exception(f"结果文件不存在: {result_path}")
#
#         try:
#             # 读取并验证结果数据
#             result_data = self._read_result_file(result_path)
#             if not result_data:
#                 self.handel_exception("无法读取或解析结果文件")
#
#             # 验证数据有效性
#             data_length = self._validate_result_data(result_data)
#             if data_length == 0:
#                 self.handel_exception("结果文件中没有有效数据")
#
#             # 创建任务处理结果
#             ws_handler.current_video_path = result_path  # 使用result_path作为标识符
#             asyncio.create_task(self._send_result_data(ws_handler, result_data, fps))
#
#             self.write(
#                 {
#                     "status": "success",
#                     "message": f"结果处理任务已准备就绪，等待播放命令，将按{fps}fps的帧率发送结果",
#                     "data_length": data_length,
#                     "fps": fps,
#                     "result_path": result_path,
#                 }
#             )
#         except Exception as e:
#             self.handel_exception(f"处理结果文件时出错: {str(e)}")
#
#     def _read_result_file(self, file_path):
#         """读取结果文件并返回JSON数据"""
#         try:
#             with open(file_path, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except (json.JSONDecodeError, IOError) as e:
#             logger.error(f"读取结果文件失败: {str(e)}")
#             return None
#
#     def _validate_result_data(self, result_data):
#         """验证结果数据并返回有效数据长度"""
#         # 获取关键数据列表
#         au_occ_list = result_data.get("au_occurrence", [])
#         au_int_list = result_data.get("au_intensity", [])
#         va_result_list = result_data.get("valence_arousal", [])
#
#         # 计算有效数据长度
#         if au_occ_list and au_int_list and va_result_list:
#             return min(len(au_occ_list), len(au_int_list), len(va_result_list))
#         return 0
#
#     async def _send_result_data(self, ws_handler, result_data, fps=5):
#         """
#         按指定帧率发送结果数据
#
#         @param ws_handler: WebSocket处理器
#         @param result_data: 结果数据
#         @param fps: 每秒帧数，默认5fps
#         """
#         try:
#             # 获取数据
#             au_occ_list = result_data.get("au_occurrence", [])
#             au_int_list = result_data.get("au_intensity", [])
#             va_result_list = result_data.get("valence_arousal", [])
#
#             # 获取数据长度
#             data_length = (
#                 min(len(au_occ_list), len(au_int_list), len(va_result_list))
#                 if au_occ_list and au_int_list and va_result_list
#                 else 0
#             )
#
#             if data_length == 0:
#                 error_message = {"type": "error", "message": "结果数据为空，无法发送"}
#                 await ws_handler._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#                 return
#
#             # 计算发送间隔
#             frame_delay = 1.0 / fps  # 0.2秒每帧
#             logger.info(f"准备发送结果数据: 总帧数 {data_length}, FPS {fps}, 每帧间隔 {frame_delay}秒")
#
#             # 发送初始信息
#             init_message = {
#                 "type": "result_info",
#                 "total_frames": data_length,
#                 "fps": fps,
#                 "frame_delay": frame_delay,
#             }
#             await ws_handler._safe_write_message(json.dumps(init_message, ensure_ascii=False))
#
#             ws_handler.is_paused = True  # 初始状态为暂停
#             ws_handler.stop_tasks = False
#             ws_handler.current_frame_index = 0
#             ws_handler.result_data = result_data
#
#             status_notification = {
#                 "type": "status_change",
#                 "status": "ready",
#                 "message": "结果数据准备就绪，等待播放命令",
#                 "total_frames": data_length,
#             }
#             await ws_handler._safe_write_message(json.dumps(status_notification, ensure_ascii=False))
#             logger.info(f"结果数据已准备就绪，等待客户端发送播放命令")
#             return
#
#         except Exception as e:
#             error_msg = f"处理结果数据时出错: {str(e)}"
#             logger.error(error_msg)
#             error_message = {"type": "error", "message": error_msg}
#             await ws_handler._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#
#
# class WebSocketHandler(tornado.websocket.WebSocketHandler):
#     def initialize(self):
#         if "ws_handlers" not in self.application.settings:
#             self.application.settings["ws_handlers"] = []
#         self.application.settings["ws_handlers"].append(self)
#         self.frame_task = None
#         self.stop_tasks = False
#         self.is_paused = True
#         self.current_video_path = None
#         self.current_frame_index = 0
#
#     def check_origin(self, origin):
#         return True
#
#     def open(self):
#         """
#         WebSocket连接建立时的处理函数
#
#         功能:
#         1. 管理WebSocket连接实例
#         2. 处理旧连接的清理
#         3. 初始化新连接的状态
#         """
#         try:
#             # 获取WebSocket处理器映射
#             ws_handler_map = self.application.settings.setdefault("ws_handler_map", {})
#
#             # 处理已存在的连接
#             self._cleanup_existing_connection(ws_handler_map)
#
#             # 初始化新连接
#             self.client_id = str(uuid.uuid4())
#             ws_handler_map["websocket_id"] = self
#             self.stop_tasks = False
#
#             # 记录连接信息
#             client_info = {
#                 "id": self.client_id,
#                 "ip": self.request.remote_ip,
#                 "time": datetime.datetime.now().isoformat(),
#                 "user_agent": self.request.headers.get("User-Agent", "未知"),
#             }
#             logger.info(f"WebSocket已连接: {json.dumps(client_info, ensure_ascii=False)}")
#
#             # 发送欢迎消息
#             welcome_message = {
#                 "type": "connection_established",
#                 "client_id": self.client_id,
#                 "server_time": datetime.datetime.now().isoformat(),
#                 "message": "WebSocket连接已建立",
#             }
#             asyncio.create_task(self._safe_write_message(json.dumps(welcome_message, ensure_ascii=False)))
#         except Exception as e:
#             logger.error(f"WebSocket连接建立过程中出错: {str(e)}", exc_info=True)
#             # 尝试关闭连接
#             try:
#                 self.close(code=1011, reason=f"服务器内部错误: {str(e)}")
#             except:
#                 pass
#
#     def _cleanup_existing_connection(self, ws_handler_map):
#         """
#         清理已存在的WebSocket连接
#
#         @param ws_handler_map: WebSocket处理器映射
#         """
#         old_handler = ws_handler_map.get("websocket_id")
#         if old_handler:
#             logger.info(f"发现已存在的WebSocket连接(ID: {getattr(old_handler, 'client_id', '未知')}), 正在关闭...")
#
#             try:
#                 # 停止任务
#                 old_handler.stop_tasks = True
#
#                 # 取消帧任务
#                 if hasattr(old_handler, "frame_task") and old_handler.frame_task and not old_handler.frame_task.done():
#                     old_handler.frame_task.cancel()
#                     logger.debug("已取消旧连接的帧任务")
#
#                 # 发送关闭通知
#                 close_message = {
#                     "type": "connection_closed",
#                     "reason": "新的客户端连接已建立",
#                     "server_time": datetime.datetime.now().isoformat(),
#                 }
#                 try:
#                     old_handler.write_message(json.dumps(close_message, ensure_ascii=False))
#                 except:
#                     pass
#
#                 # 关闭连接
#                 old_handler.close(code=1000, reason="新的客户端连接已建立")
#                 logger.info("旧的WebSocket连接已成功关闭")
#             except Exception as e:
#                 logger.warning(f"关闭旧的WebSocket连接时出错: {str(e)}")
#
#     def send_message(self, message):
#         """发送消息到WebSocket客户端"""
#         try:
#             if not self.ws_connection:
#                 logger.warning("尝试发送消息，但WebSocket连接已关闭")
#                 return False
#             self.write_message(message)
#             return True
#         except Exception as e:
#             logger.error(f"发送WebSocket消息时出错: {str(e)}")
#             return False
#
#     def on_message(self, message):
#         """
#         处理从客户端接收的WebSocket消息
#
#         支持的操作:
#         - play_video: 播放视频
#         - pause_video: 暂停视频
#         - resume_video: 恢复播放
#         - stop_video: 停止播放
#         - replay_video: 重新播放
#         - set_video_path: 设置视频路径
#
#         @param message: 客户端发送的消息
#         """
#         try:
#             # 解析消息
#             data = tornado.escape.json_decode(message)
#             logger.info(f"收到客户端消息: {json.dumps(data, ensure_ascii=False)}")
#
#             # 如果没有action字段，返回通用响应
#             if "action" not in data:
#                 return self._send_response("received", "消息已收到")
#
#             # 根据action分发到对应的处理方法
#             action = data["action"]
#             action_handlers = {
#                 "play_video": self._handle_play_video,
#                 "pause_video": self._handle_pause_video,
#                 "resume_video": self._handle_resume_video,
#                 "stop_video": self._handle_stop_video,
#                 "replay_video": self._handle_replay_video,
#                 "set_video_path": self._handle_set_video_path,
#             }
#
#             # 调用对应的处理方法
#             handler = action_handlers.get(action)
#             if handler:
#                 return handler(data)
#
#             # 未知命令处理
#             logger.warning(f"未知的视频控制命令: {action}")
#             return self._send_response("warning", f"未知的命令: {action}")
#
#         except json.JSONDecodeError:
#             logger.error("接收到无效的JSON格式消息")
#             return self._send_response("error", "无效的JSON格式")
#         except Exception as e:
#             logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
#             return self._send_response("error", f"处理消息时出错: {str(e)}")
#
#     def _send_response(self, status, message, **kwargs):
#         """
#         发送统一格式的响应
#
#         @param status: 状态 (success/error/warning/received)
#         @param message: 消息内容
#         @param kwargs: 其他要包含在响应中的字段
#         :return: 是否发送成功
#         """
#         response = {"status": status, "message": message}
#         response.update(kwargs)
#         return self.send_message(json.dumps(response, ensure_ascii=False))
#
#     def _handle_play_video(self, data):
#         """处理播放视频命令"""
#         # 1. 检查并设置视频路径
#         if not self.current_video_path and "video_path" in data:
#             self.current_video_path = data["video_path"]
#             logger.info(f"从客户端设置视频路径: {self.current_video_path}")
#
#         # 2. 验证视频路径
#         if not self.current_video_path:
#             return self._send_response("error", "暂无视频路径")
#
#         # 3. 处理结果数据播放
#         if hasattr(self, "result_data") and self.result_data:
#             return self._play_result_data_task(data)
#
#         # 4. 处理视频流播放
#         if not self.frame_task or self.frame_task.done():
#             return self._start_new_video_task(data)
#
#         # 5. 恢复已有任务
#         response = self.video_status(action="resume")
#         return self._send_response(**response)
#
#     def _play_result_data_task(self, data):
#         """启动结果数据播放任务"""
#         try:
#             logger.info("开始播放已准备的结果数据")
#             fps = data.get("fps", 5)  # 默认5fps
#             loop = tornado.ioloop.IOLoop.current().asyncio_loop
#             self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
#             self.is_paused = False
#             return self._send_response("success", "开始播放结果数据", video_path=self.current_video_path)
#         except Exception as e:
#             logger.error(f"启动结果数据播放任务失败: {str(e)}", exc_info=True)
#             return self._send_response("error", f"启动结果数据播放任务失败: {str(e)}")
#
#     def _start_new_video_task(self, data):
#         """启动新的视频播放任务"""
#         try:
#             logger.info(f"启动播放任务: {self.current_video_path}")
#             task = self.start_video_streaming(self.current_video_path)
#             if not task:
#                 return self._send_response("error", "启动播放任务失败")
#
#             # 设置为不暂停，开始播放
#             self.is_paused = False
#             return self._send_response("success", "开始播放数据", video_path=self.current_video_path)
#         except Exception as e:
#             logger.error(f"启动播放任务时出错: {str(e)}", exc_info=True)
#             return self._send_response("error", f"启动播放任务时出错: {str(e)}")
#
#     def _handle_pause_video(self, data):
#         """处理暂停视频命令"""
#         response = self.video_status(action="pause")
#         return self._send_response(**response)
#
#     def _handle_resume_video(self, data):
#         """处理恢复播放命令"""
#         # 1. 检查是否有任务运行
#         if not self.frame_task or self.frame_task.done():
#             # 2. 验证视频路径
#             if not self.current_video_path:
#                 return self._send_response("error", "暂无恢复视频")
#
#             # 3. 处理结果数据恢复
#             if hasattr(self, "result_data") and self.result_data:
#                 return self._resume_result_data_task(data)
#
#             # 4. 创建新任务
#             return self._resume_with_new_task(data)
#
#         # 5. 恢复已有任务
#         response = self.video_status(action="resume")
#         return self._send_response(**response)
#
#     def _resume_result_data_task(self, data):
#         """恢复结果数据播放任务"""
#         try:
#             logger.info("恢复播放准备的结果数据")
#             fps = data.get("fps", 5)  # 默认5fps
#             loop = tornado.ioloop.IOLoop.current().asyncio_loop
#             self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
#             self.is_paused = False
#             return self._send_response("success", "恢复播放结果数据", video_path=self.current_video_path)
#         except Exception as e:
#             logger.error(f"恢复结果数据播放失败: {str(e)}", exc_info=True)
#             return self._send_response("error", f"恢复结果数据播放失败: {str(e)}")
#
#     def _resume_with_new_task(self, data):
#         """使用新任务恢复播放"""
#         try:
#             logger.info(f"恢复播放时创建新任务: {self.current_video_path}")
#             task = self.start_video_streaming(self.current_video_path)
#             if not task:
#                 return self._send_response("error", "启动播放任务失败")
#
#             self.is_paused = False
#             return self._send_response("success", "开始播放数据", video_path=self.current_video_path)
#         except Exception as e:
#             logger.error(f"恢复播放时创建任务失败: {str(e)}", exc_info=True)
#             return self._send_response("error", f"启动播放任务时出错: {str(e)}")
#
#     def _handle_stop_video(self, data):
#         """处理停止视频命令"""
#         self.stop_sending()
#         return self._send_response("success", "数据播放已停止")
#
#     def _handle_replay_video(self, data):
#         """处理重播视频命令"""
#         # 1. 验证视频路径
#         if not self.current_video_path:
#             return self._send_response("error", "没有可重播的视频")
#
#         # 2. 处理结果数据重播
#         if hasattr(self, "result_data") and self.result_data:
#             return self._replay_result_data(data)
#
#         # 3. 重新开始视频任务
#         return self._replay_video_task(data)
#
#     def _replay_result_data(self, data):
#         """重播结果数据"""
#         try:
#             self.stop_sending()
#             fps = data.get("fps", 5)  # 默认5fps
#
#             # 重置帧索引并启动新任务
#             self.current_frame_index = 0
#             loop = tornado.ioloop.IOLoop.current().asyncio_loop
#             self.frame_task = asyncio.ensure_future(self._play_result_data(fps), loop=loop)
#             self.is_paused = False
#             return self._send_response("success", "结果数据已重新开始播放")
#         except Exception as e:
#             logger.error(f"重播结果数据时出错: {str(e)}", exc_info=True)
#             return self._send_response("error", f"重播结果数据时出错: {str(e)}")
#
#     def _replay_video_task(self, data):
#         """重播视频任务"""
#         try:
#             self.stop_sending()
#             fps = data.get("fps", None)
#             task = self.start_video_streaming(self.current_video_path, fps)
#
#             if not task:
#                 return self._send_response("error", "启动重播任务失败")
#
#             # 立即开始播放，不等待play命令
#             self.is_paused = False
#             return self._send_response("success", "数据播放已重新开始")
#         except Exception as e:
#             logger.error(f"重播视频时出错: {str(e)}", exc_info=True)
#             return self._send_response("error", f"重播数据时出错: {str(e)}")
#
#     def _handle_set_video_path(self, data):
#         """处理设置视频路径命令"""
#         if "video_path" not in data:
#             return self._send_response("error", "缺少video_path参数")
#
#         self.current_video_path = data["video_path"]
#         logger.info(f"设置视频路径: {self.current_video_path}")
#
#         # 检查视频文件是否存在
#         if not os.path.exists(self.current_video_path):
#             logger.warning(f"设置的视频路径不存在: {self.current_video_path}")
#             return self._send_response(
#                 "warning", "视频路径已设置，但文件可能不存在", video_path=self.current_video_path
#             )
#
#         return self._send_response("success", "视频路径已设置", video_path=self.current_video_path)
#
#     # 以下是一些辅助方法，用于提高代码的可维护性和健壮性
#
#     def _validate_video_path(self):
#         """验证当前视频路径是否有效"""
#         if not self.current_video_path:
#             logger.warning("当前没有设置视频路径")
#             return False
#
#         if not os.path.exists(self.current_video_path):
#             logger.warning(f"视频路径不存在: {self.current_video_path}")
#             return False
#
#         return True
#
#     def _get_task_status(self):
#         """获取当前任务状态"""
#         status = {
#             "has_task": self.frame_task is not None and not self.frame_task.done(),
#             "is_paused": self.is_paused,
#             "current_frame": self.current_frame_index,
#             "has_result_data": hasattr(self, "result_data") and bool(self.result_data),
#             "video_path": self.current_video_path,
#         }
#         return status
#
#     def _create_status_notification(self, status, additional_info=None):
#         """创建状态变更通知"""
#         notification = {
#             "type": "status_change",
#             "status": status,
#             "current_frame": self.current_frame_index,
#             "timestamp": datetime.datetime.now().isoformat(),
#         }
#
#         if additional_info:
#             notification.update(additional_info)
#
#         return notification
#
#     def stop_sending(self):
#         """停止所有发送任务"""
#         try:
#             # 设置停止标志
#             self.stop_tasks = True
#
#             # 取消帧任务
#             if self.frame_task and not self.frame_task.done():
#                 self.frame_task.cancel()
#
#             # 重置状态
#             self.is_paused = True
#
#             # 发送状态通知
#             status_notification = self._create_status_notification("stopped")
#             asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
#
#             logger.info("已停止所有发送任务")
#             return True
#         except Exception as e:
#             logger.error(f"停止发送任务时出错: {str(e)}", exc_info=True)
#             return False
#
#     async def _play_result_data(self, fps=5):
#         """
#         播放结果数据
#
#         @param fps: 每秒帧数，默认5fps
#         """
#         try:
#             if not hasattr(self, "result_data") or not self.result_data:
#                 logger.error("没有可用的结果数据")
#                 await self._safe_write_message(
#                     json.dumps({"type": "error", "message": "没有可用的结果数据"}, ensure_ascii=False)
#                 )
#                 return
#
#             # 获取数据
#             result_data = self.result_data
#             au_occ_list = result_data.get("au_occurrence", [])
#             au_int_list = result_data.get("au_intensity", [])
#             va_result_list = result_data.get("valence_arousal", [])
#
#             # 获取数据长度
#             data_length = (
#                 min(len(au_occ_list), len(au_int_list), len(va_result_list))
#                 if au_occ_list and au_int_list and va_result_list
#                 else 0
#             )
#
#             if data_length == 0:
#                 logger.error("结果数据为空")
#                 await self._safe_write_message(
#                     json.dumps({"type": "error", "message": "结果数据为空"}, ensure_ascii=False)
#                 )
#                 return
#
#             # 计算发送间隔
#             frame_delay = 1.0 / fps
#
#             # 发送开始播放通知
#             start_notification = self._create_status_notification(
#                 "playing", {"total_frames": data_length, "fps": fps, "frame_delay": frame_delay}
#             )
#             await self._safe_write_message(json.dumps(start_notification, ensure_ascii=False))
#
#             # 从当前帧开始播放
#             start_frame = self.current_frame_index
#             logger.info(f"开始播放结果数据: 从帧 {start_frame}/{data_length} 开始, FPS {fps}")
#
#             # 主循环
#             for i in range(start_frame, data_length):
#                 # 检查是否需要停止
#                 if self.stop_tasks:
#                     logger.info("检测到停止标志，结束播放")
#                     break
#
#                 # 检查是否暂停
#                 while self.is_paused and not self.stop_tasks:
#                     await asyncio.sleep(0.1)  # 暂停时小睡，减少CPU使用
#
#                 # 如果在暂停后收到了停止信号，则退出
#                 if self.stop_tasks:
#                     break
#
#                 # 更新当前帧索引
#                 self.current_frame_index = i
#
#                 # 构建帧数据
#                 frame_data = {
#                     "type": "frame_data",
#                     "frame_index": i,
#                     "total_frames": data_length,
#                     "au_occurrence": au_occ_list[i] if i < len(au_occ_list) else None,
#                     "au_intensity": au_int_list[i] if i < len(au_int_list) else None,
#                     "valence_arousal": va_result_list[i] if i < len(va_result_list) else None,
#                     "timestamp": datetime.datetime.now().isoformat(),
#                 }
#
#                 # 发送帧数据
#                 success = await self._safe_write_message(json.dumps(frame_data, ensure_ascii=False))
#                 if not success:
#                     logger.error(f"发送帧 {i} 数据失败，停止播放")
#                     break
#
#                 # 按帧率延迟
#                 await asyncio.sleep(frame_delay)
#
#             # 播放完成或被中断
#             if self.current_frame_index >= data_length - 1 and not self.stop_tasks:
#                 # 正常播放完成
#                 complete_notification = self._create_status_notification("completed", {"message": "结果数据播放完成"})
#                 await self._safe_write_message(json.dumps(complete_notification, ensure_ascii=False))
#                 logger.info("结果数据播放完成")
#             elif self.stop_tasks:
#                 # 被手动停止
#                 logger.info(f"结果数据播放被停止，当前帧: {self.current_frame_index}/{data_length}")
#
#         except asyncio.CancelledError:
#             logger.info(f"结果数据播放任务被取消，当前帧: {self.current_frame_index}")
#         except Exception as e:
#             logger.error(f"播放结果数据时出错: {str(e)}", exc_info=True)
#             error_notification = {
#                 "type": "error",
#                 "message": f"播放结果数据时出错: {str(e)}",
#                 "current_frame": self.current_frame_index,
#             }
#             await self._safe_write_message(json.dumps(error_notification, ensure_ascii=False))
#
#     async def _safe_write_message(self, message):
#         """
#         安全地发送WebSocket消息
#
#         @param message: 要发送的消息
#         :return: 是否发送成功
#         """
#         try:
#             if not self.ws_connection:
#                 logger.warning("尝试发送消息，但WebSocket连接已关闭")
#                 return False
#
#             self.write_message(message)
#             return True
#         except tornado.websocket.WebSocketClosedError:
#             logger.warning("WebSocket连接已关闭，无法发送消息")
#             return False
#         except Exception as e:
#             logger.error(f"发送WebSocket消息时出错: {str(e)}")
#             return False
#
#     def on_close(self):
#         """WebSocket连接关闭时的处理函数"""
#         try:
#             # 停止所有任务
#             self.stop_sending()
#
#             # 从处理器映射中移除
#             if hasattr(self.application, "settings") and "ws_handler_map" in self.application.settings:
#                 ws_handler_map = self.application.settings["ws_handler_map"]
#                 if ws_handler_map.get("websocket_id") == self:
#                     ws_handler_map.pop("websocket_id", None)
#
#             # 从处理器列表中移除
#             if hasattr(self.application, "settings") and "ws_handlers" in self.application.settings:
#                 if self in self.application.settings["ws_handlers"]:
#                     self.application.settings["ws_handlers"].remove(self)
#
#             logger.info(f"WebSocket已关闭，客户端ID: {getattr(self, 'client_id', '未知')}")
#         except Exception as e:
#             logger.error(f"处理WebSocket关闭时出错: {str(e)}", exc_info=True)
#
#     def video_status(self, action):
#         """
#         控制数据播放的暂停和恢复
#
#         @param action: 控制动作，可选值："pause"暂停播放，"resume"恢复播放
#         :return: 处理结果
#         """
#         logger.info(f"收到控制命令: {action}")
#
#         if action == "pause":
#             if not self.frame_task or self.frame_task.done():
#                 logger.warning("尝试暂停播放，但没有正在播放的任务")
#                 return {"status": "error", "message": "没有正在播放的数据"}
#
#             if self.is_paused:
#                 logger.info("播放已经处于暂停状态")
#                 return {"status": "warning", "message": "播放已经处于暂停状态"}
#
#             self.is_paused = True
#             status_notification = {
#                 "type": "status_change",
#                 "status": "paused",
#                 "current_frame": self.current_frame_index,
#                 "timestamp": datetime.datetime.now().isoformat(),
#             }
#             asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
#             logger.info(f"播放已暂停，当前帧: {self.current_frame_index}")
#             return {
#                 "status": "success",
#                 "message": "播放已暂停",
#                 "action": "paused",
#                 "current_frame": self.current_frame_index,
#             }
#
#         elif action == "resume":
#             if not self.frame_task or self.frame_task.done():
#                 logger.warning("尝试恢复播放，但没有可用的任务")
#                 if self.current_video_path:
#                     return {"status": "info", "message": "需要先启动播放任务", "action": "need_start"}
#                 else:
#                     return {"status": "error", "message": "没有可播放的数据"}
#
#             if not self.is_paused:
#                 logger.info("播放已经在进行中")
#                 return {"status": "warning", "message": "播放已经在进行中"}
#
#             # 取消暂停标志
#             self.is_paused = False
#             status_notification = {
#                 "type": "status_change",
#                 "status": "resumed",
#                 "current_frame": self.current_frame_index,
#                 "timestamp": datetime.datetime.now().isoformat(),
#             }
#             asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
#             logger.info(f"播放已恢复，从帧 {self.current_frame_index} 开始")
#             return {
#                 "status": "success",
#                 "message": "播放已恢复",
#                 "action": "resumed",
#                 "current_frame": self.current_frame_index,
#             }
#
#         else:
#             logger.warning(f"不支持的控制动作: {action}")
#             return {"status": "error", "message": f"不支持的动作: {action}"}
#
#     def start_video_streaming(self, video_path, fps=None):
#         """
#         启动视频流发送任务
#
#         @param video_path: 视频文件路径
#         @param fps: 指定发送帧率，如果为None则使用视频原始帧率
#         """
#         logger.info(f"start_stream: {video_path}")
#         if not self.ws_connection:
#             return None
#
#         # 检查视频文件
#         if not os.path.exists(video_path):
#             return None
#
#         # 停止现有任务（如果有）
#         if self.frame_task and not self.frame_task.done():
#             logger.info("停止已存在的任务")
#             self.stop_tasks = True
#             self.frame_task.cancel()
#
#         # 重置状态
#         self.stop_tasks = False
#         self.is_paused = True  # 初始化为暂停状态，等待前端播放请求
#         self.current_frame_index = 0
#         self.current_video_path = video_path
#
#         try:
#             loop = tornado.ioloop.IOLoop.current().asyncio_loop
#             task = asyncio.ensure_future(self.send_video_stream(video_path, fps), loop=loop)
#             logger.info(f"成功创建视频流发送任务: {task}")
#             self.frame_task = task
#
#             # 告知客户端任务已创建，等待播放命令
#             status_notification = {
#                 "type": "status_change",
#                 "status": "ready",
#                 "message": "数据准备就绪，等待播放命令",
#                 "video_path": video_path,
#             }
#             asyncio.create_task(self._safe_write_message(json.dumps(status_notification, ensure_ascii=False)))
#
#             return task
#         except Exception as e:
#             logger.error(f"创建视频流发送任务时出错: {str(e)}")
#             return None
#
#     async def send_video_stream(self, video_path, fps=None):
#         """
#         处理视频控制，只发送结果数据而不发送视频数据
#
#         @param video_path: 视频文件路径，仅用于查找对应的结果文件
#         @param fps: 指定帧率，默认使用5fps
#         """
#         logger.info(f"处理视频路径: {video_path}")
#
#         try:
#             # 设置当前视频路径
#             self.current_video_path = video_path
#
#             # 固定设置为5fps
#             send_fps = 5
#             frame_delay = 1.0 / send_fps  # 0.2秒每帧
#
#             # 尝试获取结果数据路径
#             video_dir = os.path.dirname(video_path)
#             video_base_name = os.path.splitext(os.path.basename(video_path))[0]
#             possible_result_paths = [
#                 os.path.join(video_dir, f"{video_base_name}.json"),  # 同名json
#                 os.path.join(video_dir, "result.json"),  # 固定名称
#                 os.path.join(os.path.dirname(__file__), "result.json"),  # 当前目录下的result.json
#             ]
#
#             result_path = None
#             for path in possible_result_paths:
#                 if os.path.exists(path):
#                     result_path = path
#                     logger.info(f"找到结果文件: {result_path}")
#                     break
#
#             if not result_path:
#                 logger.error("未找到有效的结果文件")
#                 error_message = {"type": "error", "message": "未找到有效的结果文件"}
#                 await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#                 return
#
#             # 加载结果数据
#             try:
#                 with open(result_path, "r", encoding="utf-8") as f:
#                     result_data = json.load(f)
#
#                 # 获取数据
#                 au_occ_list = result_data.get("au_occurrence", [])
#                 au_int_list = result_data.get("au_intensity", [])
#                 va_result_list = result_data.get("valence_arousal", [])
#                 personality = result_data.get("personality", [])
#                 depression = result_data.get("depression", [])
#                 expression = result_data.get("expression", [])
#                 global_blendshape = result_data.get("global_blendshape", [])
#
#                 # 获取数据长度
#                 data_length = (
#                     min(len(au_occ_list), len(au_int_list), len(va_result_list))
#                     if au_occ_list and au_int_list and va_result_list
#                     else 0
#                 )
#
#                 if data_length == 0:
#                     logger.error(f"结果文件 {result_path} 中没有有效数据")
#                     error_message = {"type": "error", "message": "结果文件中没有有效数据"}
#                     await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#                     return
#
#                 # 发送结果文件信息
#                 file_info = {
#                     "type": "result_info",
#                     "result_path": result_path,
#                     "data_length": data_length,
#                     "fps": send_fps,
#                     "frame_delay": frame_delay,
#                     "video_path": video_path,
#                 }
#                 await self._safe_write_message(json.dumps(file_info, ensure_ascii=False))
#                 logger.info(f"开始发送结果数据: 总帧数 {data_length}, FPS {send_fps}, 每帧间隔 {frame_delay}秒")
#
#                 # 发送结果数据
#                 frame_index = 0
#                 self.current_frame_index = 0
#
#                 while frame_index < data_length and not self.stop_tasks:
#                     # 检查暂停状态
#                     if self.is_paused:
#                         logger.info(f"数据发送暂停中，当前帧：{frame_index}")
#                         # 当暂停时，循环等待直到恢复播放或停止
#                         while self.is_paused and not self.stop_tasks:
#                             # 每0.1秒检查一次状态
#                             await asyncio.sleep(0.1)
#
#                         # 如果循环是因为stop_tasks退出的，则跳出外层循环
#                         if self.stop_tasks:
#                             logger.info("暂停状态中收到停止命令，终止数据发送")
#                             break
#
#                         logger.info(f"数据发送已恢复，继续从帧 {frame_index} 开始")
#
#                     # 构建当前帧的结果数据
#                     frame_data = {
#                         "type": "frame_data",
#                         "frame_index": frame_index,
#                         "total_frames": data_length,
#                         "timestamp": datetime.datetime.now().isoformat(),
#                     }
#
#                     # 添加AU occurrence数据
#                     if frame_index < len(au_occ_list):
#                         frame_data["au_occurrence"] = au_occ_list[frame_index]
#
#                     # 添加AU intensity数据
#                     if frame_index < len(au_int_list):
#                         frame_data["au_intensity"] = au_int_list[frame_index]
#
#                     # 添加VA结果数据
#                     if frame_index < len(va_result_list):
#                         frame_data["valence_arousal"] = va_result_list[frame_index]
#
#                     # 发送数据
#                     await self._safe_write_message(json.dumps(frame_data, ensure_ascii=False))
#
#                     # 每50帧打印一次日志
#                     if frame_index % 50 == 0:
#                         logger.info(
#                             f"数据发送进度: {frame_index}/{data_length} 帧 ({round(frame_index/data_length*100, 1)}%)"
#                         )
#
#                     # 更新帧索引
#                     frame_index += 1
#                     self.current_frame_index = frame_index
#
#                     # 控制发送速度
#                     await asyncio.sleep(frame_delay)
#
#                 # 发送完成消息
#                 if not self.stop_tasks:
#                     complete_message = {"type": "complete", "message": f"数据发送完成，共 {data_length} 帧"}
#                     await self._safe_write_message(json.dumps(complete_message, ensure_ascii=False))
#                     logger.info(f"数据发送完成，共 {data_length} 帧")
#
#             except Exception as e:
#                 error_msg = f"处理结果文件时出错: {str(e)}"
#                 logger.error(error_msg)
#                 error_message = {"type": "error", "message": error_msg}
#                 await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#
#         except Exception as e:
#             logger.error(f"处理数据时出错: {str(e)}")
#             if self.ws_connection:
#                 error_message = {"type": "error", "message": f"处理数据时出错: {str(e)}"}
#                 await self._safe_write_message(json.dumps(error_message, ensure_ascii=False))
#
#
# def make_app():
#     return tornado.web.Application(
#         [
#             (r"/upload", FaceProxy),
#             (r"/websocket", WebSocketHandler),
#             (r"/control", FaceProxy),
#             (r"/video_control", FaceProxy),  # 新增路由，用于处理GET请求的视频控制
#         ],
#     )
#
#
# if __name__ == "__main__":
#     close_port(9090)
#     try:
#         app = make_app()
#         server = tornado.httpserver.HTTPServer(app)
#         server.listen(9090, address="0.0.0.0")
#         ws_server = tornado.httpserver.HTTPServer(app)
#         ws_server.add_sockets(tornado.netutil.bind_sockets(9001))
#         tornado.ioloop.IOLoop.current().start()
#     except KeyboardInterrupt:
#         tornado.ioloop.IOLoop.current().stop()
#     except Exception as e:
#         print(f"启动服务时出错: {e}")
