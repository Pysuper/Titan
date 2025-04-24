"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/24 14:17
@Desc    ：请求重试装饰器
"""

import functools
import json
import time
from typing import Any, Callable

import requests
from requests.exceptions import RequestException

from logic.config import logic as logger


def send_to_url(url: str, max_retries: int = 3, retry_interval: int = 2, timeout: int = 10):
    """
    装饰器：将函数返回的结果发送到指定URL

    :param url: 目标服务器URL
    :param max_retries: 最大重试次数
    :param retry_interval: 重试间隔（秒）
    :param timeout: 请求超时时间（秒）
    :return: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 执行原始函数获取结果
            result = func(*args, **kwargs)

            # 发送结果到指定URL
            send_success = _send_result(result, url, max_retries, retry_interval, timeout)

            # 返回原始结果和发送状态
            return result, send_success

        return wrapper

    return decorator


def _send_result(result: Any, url: str, max_retries: int = 3, retry_interval: int = 2, timeout: int = 10) -> bool:
    """
    使用POST请求，将算法结果发送到指定服务器，自动重连

    :param result: 结果
    :param url: 目标服务器URL
    :param max_retries: 最大重试次数
    :param retry_interval: 重试间隔（秒）
    :param timeout: 请求超时时间（秒）
    :return: 发送状态：True/False
    """
    # 尝试将结果转换为JSON
    try:
        if hasattr(result, "__dict__"):
            # 如果结果是对象，尝试转换其属性为字典
            payload = result.__dict__
        elif isinstance(result, dict):
            # 如果已经是字典，直接使用
            payload = result
        else:
            # 尝试使用json序列化
            payload = json.loads(json.dumps(result))
    except (TypeError, json.JSONDecodeError) as e:
        logger.error(f"结果序列化失败: {str(e)}")
        return False

    # 添加时间戳
    payload["timestamp"] = time.time()

    # 设置请求头
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # 重试逻辑
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"正在发送结果到 {url}，第 {attempt} 次尝试...")
            response = requests.post(url=url, json=payload, headers=headers, timeout=timeout)

            # 检查响应状态码
            if response.status_code in (200, 201, 202):
                try:
                    response_data = response.json()
                    logger.info(f"发送成功，服务器响应: {response_data}")
                    return True
                except json.JSONDecodeError:
                    logger.error(f"发送成功，但服务器响应不是有效的JSON: {response.text}")
                    return True
            else:
                logger.info(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")

                # 如果是最后一次尝试，返回失败
                if attempt == max_retries:
                    return False

                # 否则等待后重试
                time.sleep(retry_interval)

        except RequestException as e:
            logger.warning(f"请求异常: {str(e)}")

            # 如果是最后一次尝试，返回失败
            if attempt == max_retries:
                return False

            # 否则等待后重试
            logger.warning(f"将在 {retry_interval} 秒后重试...")
            time.sleep(retry_interval)

    # 如果所有尝试都失败
    return False
