"""
@Project ：Backend
@File    ：requests.py
@Author  ：PySuper
@Date    ：2025/4/9 15:27
@Desc    ：请求中间件，记录请求和响应信息
"""

import json
import time

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from platform.logic.config import logic as logger


class RequestMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def process_request(self, request: HttpRequest):
        """
        处理请求
        """
        request.start_time = time.time()

        # 记录请求信息
        request_info = {
            "method": request.method,
            "path": request.path,
            "query_params": request.GET.dict(),
            "headers": dict(request.headers),
            "body": self._get_request_body(request),
            "client_ip": self._get_client_ip(request),
        }

        logger.info(f"Incoming request: {json.dumps(request_info, indent=2)}")

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse):
        """
        处理响应
        """
        # 计算请求处理时间
        duration = time.time() - request.start_time

        # 记录响应信息
        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": self._get_response_body(response),
            "duration": f"{duration:.2f}s",
        }

        logger.info(f"Outgoing response: {json.dumps(response_info, indent=2)}")

        return response

    def _get_request_body(self, request: HttpRequest):
        """
        获取请求体
        """
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                return json.loads(request.body)
            except json.JSONDecodeError:
                return request.body.decode("utf-8")
        return None

    def _get_response_body(self, response: HttpResponse):
        """
        获取响应体
        """
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return response.content.decode("utf-8")

    def _get_client_ip(self, request: HttpRequest):
        """
        获取客户端IP地址
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
