"""
@Project ：Titan
@File    ：http.py
@Author  ：PySuper
@Date    ：2025/4/28 11:38
@Desc    ：Titan http.py
"""

import datetime
import json
import traceback
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

import tornado.web
import tornado.websocket

# 修改导入
from config.files import UPLOAD_DIR
from logic.config import get_logger

# 创建请求ID上下文变量
request_id_var = ContextVar("request_id", default=None)


# 为loguru创建过滤器函数
def request_id_filter(record):
    """为日志记录添加请求ID"""
    request_id = request_id_var.get()
    record["extra"].update({"request_id": request_id or "no-request-id"})
    return True


# 获取配置了过滤器的logger
logger = get_logger("proxy")

# 使用loguru的方式添加过滤器
logger = logger.bind(request_id="no-request-id")

from enum import Enum


class ResponseStatus(str, Enum):
    """响应状态枚举"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SavedFile:
    """保存的文件信息"""

    original_name: str
    saved_name: str
    file_path: str
    file_size: int
    content_type: str
    upload_time: str
    unique_id: str


class JSONEncoder(json.JSONEncoder):
    """扩展的JSON编码器，支持更多Python类型"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


class CustomHttp(tornado.web.RequestHandler):
    """
    自定义HTTP请求处理类，提供通用的请求处理功能

    该类扩展了Tornado的RequestHandler，提供了以下增强功能：
    - 自动请求日志记录
    - 统一的错误和成功响应格式
    - 跨域支持
    - 文件上传处理
    - WebSocket通知
    - 参数提取和验证
    - 异常处理
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初始化请求相关属性
        self.client_ip = self.request.remote_ip
        self.start_time = datetime.datetime.now()
        self._request_id = str(uuid.uuid4())

        # 设置请求ID上下文
        request_id_var.set(self._request_id)

        # 为当前请求绑定请求ID到logger
        global logger
        logger = logger.bind(request_id=self._request_id)

        # 设置默认HTTP响应头
        self.set_default_headers()

        # 记录请求日志
        logger.debug(f"收到请求==> 来自 {self.client_ip} - {self.request.method} {self.request.uri}")

    def http_err(self, msg: str, status_code: int = 400) -> None:
        """
        返回HTTP错误响应

        Args:
            msg: 错误信息
            status_code: HTTP状态码，默认为400
        """
        logger.error(f"HTTP错误 [{self._request_id}]: {msg}")
        self.set_status(status_code)
        self.write({"status": ResponseStatus.ERROR, "message": msg, "request_id": self._request_id})
        return None

    def http_success(self, data: Any = None, message: str = "操作成功") -> None:
        """
        返回HTTP成功响应

        Args:
            data: 响应数据
            message: 成功消息
        """
        response = {"status": ResponseStatus.SUCCESS, "message": message, "request_id": self._request_id}

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

    def save(self, files: List[Dict[str, Any]]) -> List[SavedFile]:
        """
        保存上传的文件

        Args:
            files: 上传的文件列表

        Returns:
            保存的文件信息列表
        """
        saved_files = []

        # 确保上传目录存在
        upload_path = Path(UPLOAD_DIR)
        upload_path.mkdir(parents=True, exist_ok=True)

        for file_data in files:
            original_filename = file_data["filename"]
            file_content = file_data["body"]
            content_type = file_data["content_type"]

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}_{original_filename}"
            file_path = upload_path / filename

            try:
                file_path.write_bytes(file_content)

                file_info = SavedFile(
                    original_name=original_filename,
                    saved_name=filename,
                    file_path=str(file_path),
                    file_size=len(file_content),
                    content_type=content_type,
                    upload_time=timestamp,
                    unique_id=unique_id,
                )
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

        Args:
            data: 通知数据

        Returns:
            发送是否成功
        """
        try:
            ws = self.get_ws()
            if ws:
                # 添加时间戳和请求ID
                data.update({"timestamp": datetime.datetime.now().isoformat(), "request_id": self._request_id})

                # 使用自定义编码器
                json_data = json.dumps(data, ensure_ascii=False, cls=JSONEncoder)

                if ws.send_message(json_data):
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

    def validate_params(self, required_params: List[str]) -> Optional[Dict[str, Any]]:
        """
        验证请求参数是否包含所有必需的参数

        Args:
            required_params: 必需参数列表

        Returns:
            参数字典或None（如果验证失败）
        """
        params = self.extract_params()
        # 更Pythonic的列表推导式
        missing_params = [param for param in required_params if param not in params or not params[param]]

        if missing_params:
            self.http_err(f"缺少必需参数: {', '.join(missing_params)}", 400)
            return None

        return params

    def handle_exception(self, func):
        """
        异常处理装饰器

        Args:
            func: 要装饰的函数

        Returns:
            装饰后的函数
        """

        @wraps(func)
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

    @property
    def request_id(self) -> str:
        """获取当前请求ID"""
        return self._request_id

    @property
    def request_duration(self) -> float:
        """获取请求持续时间（秒）"""
        return (datetime.datetime.now() - self.start_time).total_seconds()
