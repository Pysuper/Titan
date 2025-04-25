"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/25 14:04
@Desc    ：HTTP客户端，用于向服务器发送请求
"""

import json
import os

import requests
from loguru import logger


# TODO: 只要发送请求，就进行重试，增加日志收集、重试机制
class SendRequest:
    def __init__(self, http_server_url):
        self.http_server_url = http_server_url

    def get(self):
        pass

    def post(self, url, path):
        response = requests.post(url, data=json.dumps({"video_path": path}), timeout=10)
        if response.status_code == 200:
            logger.info(f"Success: {response.status_code} {response.text[:100]}...")
            return response.json()
        logger.error(f"Error: {response.status_code}")
        return None

    def validate(self, file_path):
        """
        校验参数
        :param file_path:
        :return:
        """
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                # 尝试读取文件确保可访问
                with open(file_path, "r") as f:
                    f.read(10)  # 只读取前10个字符确认文件可读
                logger.info(f"找到可用的结果文件: {file_path}")
                return file_path
            except Exception as e:
                logger.warning(f"文件 {file_path} 存在但无法读取: {e}")
                return None
        return None
