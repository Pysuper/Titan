"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/25 14:04
@Desc    ：HTTP客户端，用于向服务器发送请求
"""

import json
import os
from typing import Dict, Optional

import requests
from logic.config import get_logger

logger = get_logger("proxy")

from decorators.request import class_retry_decorator


@class_retry_decorator()
class SendRequest:
    """
    HTTP客户端，用于向服务器发送请求
    """

    def __init__(self, http_server_url):
        self.http_server_url = http_server_url

    def get(self, url: str, params: Dict, **kwargs) -> Optional[Dict]:
        """
        发送GET请求

        @param url: 请求URL
        @param params: 请求参数
        @param kwargs: 其他请求参数
        :return: 响应结果，失败返回None
        """
        timeout = kwargs.get("timeout", 10)
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            logger.debug(f"GET请求成功: {response.status_code} {response.text[:100]}...")
            return response.json()
        logger.error(f"GET请求错误: {response.status_code}")
        return None

    def post(self, url: str, params: Dict, **kwargs) -> Optional[Dict]:
        """
        发送POST请求

        @param url: 请求URL
        @param params: 请求参数
        @param kwargs: 其他请求参数
        :return: 响应结果，失败返回None
        """
        timeout = kwargs.get("timeout", 10)
        headers = kwargs.get("headers", {"Content-Type": "application/json"})
        response = requests.post(url, data=json.dumps(params), headers=headers, timeout=timeout)
        if response.status_code == 200:
            logger.debug(f"POST请求成功: {response.status_code} {response.text[:100]}...")
            return response.json()
        logger.error(f"POST请求错误: {response.status_code}")
        return None

    def put(self, url: str, params: Dict, **kwargs) -> Optional[Dict]:
        """
        发送PUT请求

        @param url: 请求URL
        @param params: 请求参数
        @param kwargs: 其他请求参数
        :return: 响应结果，失败返回None
        """
        timeout = kwargs.get("timeout", 10)
        headers = kwargs.get("headers", {"Content-Type": "application/json"})
        response = requests.put(url, data=json.dumps(params), headers=headers, timeout=timeout)
        if response.status_code in (200, 201, 204):
            logger.debug(f"PUT请求成功: {response.status_code} {response.text[:100]}...")
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.debug("PUT请求成功，但响应不是JSON格式")
                return {"status": "success", "status_code": response.status_code}
        logger.error(f"PUT请求错误: {response.status_code}")
        return None

    def delete(self, url: str, params: Dict, **kwargs) -> Optional[Dict]:
        """
        发送DELETE请求

        @param url: 请求URL
        @param params: 请求参数
        @param kwargs: 其他请求参数
        :return: 响应结果，失败返回None
        """
        timeout = kwargs.get("timeout", 10)
        response = requests.delete(url, params=params, timeout=timeout)
        if response.status_code in (200, 202, 204):
            logger.debug(f"DELETE请求成功: {response.status_code}")
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.debug("DELETE请求成功，但响应不是JSON格式")
                return {"status": "success", "status_code": response.status_code}
        logger.error(f"DELETE请求错误: {response.status_code}")
        return None

    def patch(self, url: str, params: Dict, **kwargs) -> Optional[Dict]:
        """
        发送PATCH请求

        @param url: 请求URL
        @param params: 请求参数
        @param kwargs: 其他请求参数
        :return: 响应结果，失败返回None
        """
        timeout = kwargs.get("timeout", 10)
        headers = kwargs.get("headers", {"Content-Type": "application/json"})
        response = requests.patch(url, data=json.dumps(params), headers=headers, timeout=timeout)
        if response.status_code in (200, 201, 204):
            logger.debug(f"PATCH请求成功: {response.status_code} {response.text[:100]}...")
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.debug("PATCH请求成功，但响应不是JSON格式")
                return {"status": "success", "status_code": response.status_code}
        logger.error(f"PATCH请求错误: {response.status_code}")
        return None

    def validate(self, params):
        """
        校验参数
        @param params:
        :return:
        """
        if os.path.exists(params) and os.path.isfile(params):
            try:
                # 尝试读取文件确保可访问
                # with open(params, "r") as f:
                with open(params) as f:
                    f.read(10)  # 只读取前10个字符确认文件可读
                logger.info(f"找到可用的结果文件:  {params}")
                return params
            except Exception as e:
                logger.warning(f"文件 { params} 存在但无法读取: {e}")
                return None
        return None
