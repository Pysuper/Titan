"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/24 14:17
@Desc    ：请求重试装饰器
"""

import functools
import inspect
import json
import time
from functools import wraps
from typing import Any, Callable, Optional
from typing import Dict

import aiohttp
import requests
from requests.exceptions import RequestException

from logic.config import logger


def send_to_url(url: str, max_retries: int = 3, retry_interval: int = 2, timeout: int = 10):
    """
    装饰器：将函数返回的结果发送到指定URL

    @param url: 目标服务器URL
    @param max_retries: 最大重试次数
    @param retry_interval: 重试间隔（秒）
    @param timeout: 请求超时时间（秒）
    :return: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
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

    @param result: 结果
    @param url: 目标服务器URL
    @param max_retries: 最大重试次数
    @param retry_interval: 重试间隔（秒）
    @param timeout: 请求超时时间（秒）
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


# 重试执行
def retry(max_attempts, delay):
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempts + 1} failed. Retrying in {delay} seconds.")
                    attempts += 1
                    time.sleep(delay)
            raise Exception("Max retry attempts exceeded.")

        return wrapper

    return decorator


# 重试装饰器
def retry_(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        raise e
                    time.sleep(delay)
                    return None
            return None

        return wrapper

    return decorator


def class_retry_decorator(max_retries: int = 3, retry_interval: int = 2, timeout: int = 10):
    """
    类装饰器：为类中的所有请求方法添加重试功能

    @param max_retries: 最大重试次数
    @param retry_interval: 重试间隔（秒）
    @param timeout: 请求超时时间（秒）
    :return: 装饰后的类
    """

    def decorator(cls):
        # 获取原始类的所有方法
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # 只装饰HTTP请求方法
            if name in ["get", "post", "put", "delete", "patch"]:
                # 使用方法装饰器替换原始方法
                setattr(cls, name, _method_retry_decorator(max_retries, retry_interval, timeout)(method))
        return cls

    return decorator


def _method_retry_decorator(max_retries: int, retry_interval: int, timeout: int):
    """
    方法装饰器：为方法添加重试功能

    @param max_retries: 最大重试次数
    @param retry_interval: 重试间隔（秒）
    @param timeout: 请求超时时间（秒）
    :return: 装饰后的方法
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, url: str, params: Dict, *args, **kwargs) -> Any:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"发送{func.__name__.upper()}请求到 {url}，第 {attempt} 次尝试...")
                    # 将timeout参数传递给原始函数
                    kwargs["timeout"] = kwargs.get("timeout", timeout)
                    result = func(self, url, params, *args, **kwargs)
                    return result
                except RequestException as e:
                    logger.warning(f"请求异常: {str(e)}")

                    # 如果是最后一次尝试，记录错误并返回None
                    if attempt == max_retries:
                        logger.error(f"已达到最大重试次数 {max_retries}，请求失败")
                        return None

                    # 否则等待后重试
                    logger.warning(f"将在 {retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
            return None

        return wrapper

    return decorator


def send_to_url_params(func):
    """
    发送结果到指定URL的装饰器
    """

    async def wrapper(self, algorithm_name, params, url, *args, **kwargs):
        # 先执行原始函数获取结果
        result = await func(self, algorithm_name, params, url, *args, **kwargs)

        # 发送结果到指定URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=result) as response:
                return await response.json()

    return wrapper


def send_to_url_util(url: Optional[str] = None):
    """
    将函数结果发送到指定URL的装饰器

    Args:
        url: 要发送结果的URL，如果为None则不发送
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 执行原始函数
            result = func(*args, **kwargs)

            # 如果提供了URL，则发送结果
            if url:
                try:
                    response = requests.post(url, json=result)
                    response.raise_for_status()
                    logger.info(f"Successfully sent result to {url}")
                except Exception as e:
                    logger.exception(f"Error sending result to {url}: {str(e)}")

            # 返回原始函数的结果
            return result

        return wrapper

    return decorator


# 限流装饰器
def rate_limit(max_calls: int, period: int):
    """
    限流装饰器

    Args:
        max_calls: 最大调用次数
        period: 限制周期（秒）
    """

    def decorator(func: Callable) -> Callable:
        last_called = time.time() - period

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal last_called
            if time.time() - last_called < period / max_calls:
                time.sleep((period / max_calls) - (time.time() - last_called))
            result = func(*args, **kwargs)
            last_called = time.time()
            return result

        return wrapper

    return decorator


# 超时装饰器
def timeout(seconds: int):
    """
    超时装饰器
    Args:
        seconds: 超时时间（秒）
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:  # 捕获所有异常
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
            return result

        return wrapper

    return decorator


@retry_(retries=5, delay=2)
def my_function():
    #  这里是你的函数实现
    pass
