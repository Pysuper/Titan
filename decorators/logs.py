"""
@Project ：Backend
@File    ：logs.py
@Author  ：PySuper
@Date    ：2025/4/23 21:09
@Desc    ：日志装饰器
"""

import functools
import logging

import time
from datetime import datetime
from typing import Any, Callable

from logic.config import get_logger

logger = get_logger(__name__)


def log_exception(func: Callable) -> Callable:
    """捕获并记录函数异常，保留原始堆栈跟踪"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise

    return wrapper


def log_execution_time(threshold: float = 0.0) -> Callable:
    """记录函数执行时间（可设置耗时阈值）"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time

            if elapsed > threshold:
                logger.warning(f"{func.__name__} took {elapsed:.4f}s (超过阈值 {threshold}s)")
            else:
                logger.info(f"{func.__name__} took {elapsed:.4f}s")

            return result

        return wrapper

    return decorator


def log_function_call(show_args: bool = True, show_return: bool = True) -> Callable:
    """增强版函数调用日志（可选参数/返回值记录）"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 参数记录
            if show_args:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                logger.debug(f"Calling {func.__name__}({signature})")
            else:
                logger.debug(f"Calling {func.__name__}")

            result = func(*args, **kwargs)

            # 返回值记录
            if show_return:
                logger.debug(f"{func.__name__} returned {type(result).__name__}({result!r})")
            else:
                logger.debug(f"{func.__name__} completed")

            return result

        return wrapper

    return decorator


def async_logger(func: Callable) -> Callable:
    """支持异步函数的日志装饰器"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        logger.info(f"Async {func.__name__} started")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Async {func.__name__} completed")
            return result
        except Exception as e:
            logger.exception(f"Async {func.__name__} failed: {str(e)}")
            raise

    return wrapper


def rate_limited(max_per_second: float):
    """API速率限制装饰器"""
    min_interval = 1.0 / max_per_second

    def decorator(func: Callable) -> Callable:
        last_called = time.monotonic()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal last_called
            elapsed = time.monotonic() - last_called
            wait = max(min_interval - elapsed, 0)
            if wait > 0:
                logger.warning(f"Rate limiting: Waiting {wait:.2f}s before calling {func.__name__}")
                time.sleep(wait)
            last_called = time.monotonic()
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_context(context_key: str):
    """在日志中添加上下文信息"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            context = getattr(args[0], context_key, None) if args else None
            extra = {context_key: context} if context else {}
            logger.info(f"Entering {func.__name__}", extra=extra)
            try:
                result = func(*args, **kwargs)
                logger.info(f"Exiting {func.__name__}", extra=extra)
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed with context {context}", extra=extra)
                raise

        return wrapper

    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0):
    """带指数退避的重试机制"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    wait = delay * (2 ** (attempts - 1))
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed. Retrying in {wait:.1f}s. Error: {str(e)}"
                    )
                    time.sleep(wait)
            return func(*args, **kwargs)  # 最后一次尝试不捕获异常

        return wrapper

    return decorator


# def validate_args(schema: dict):
#     """基于JSON Schema的参数校验"""
#
#     def decorator(func: Callable) -> Callable:
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             from jsonschema import validate
#
#             # 构建参数字典
#             parameters = inspect.signature(func).bind(*args, **kwargs).arguments
#             try:
#                 validate(instance=parameters, schema=schema)
#             except Exception as e:
#                 logger.error(f"参数校验失败: {str(e)}")
#                 raise
#             return func(*args, **kwargs)
#
#         return wrapper
#
#     return decorator


# 日志输出
def log_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        with open("results.log", "a") as log_file:
            log_file.write(f"{func.__name__} - Result: {result}\n")
        return result

    return wrapper


# 优雅的错误处理
def suppress_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            return None

    return wrapper


# 调试变得更容易
def debug(func):
    def wrapper(*args, **kwargs):
        print(f"Debugging {func.__name__} - args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper


def log_decorator(func):
    def wrapper(*args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        logging.info(f"开始执行 {func.__name__} 函数")
        result = func(*args, **kwargs)
        logging.info(f"{func.__name__} 函数执行完毕")
        return result

    return wrapper


'''


# 新增使用示例
class ExampleService:
    def __init__(self, service_id):
        self.service_id = service_id

    @log_context("service_id")
    @retry(max_attempts=3)
    @validate_args(
        schema={
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "threshold": {"type": "number", "minimum": 0},
            },
            "required": ["data"],
        }
    )
    def process_data(self, data: list, threshold: float = 0.5):
        """示例处理方法"""
        if len(data) > 1000:
            raise ValueError("Data size exceeds limit")
        return [x for x in data if x > threshold]


@async_logger
async def async_data_fetch(url: str):
    """示例异步方法"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


@rate_limited(max_per_second=5)
def api_client_request(params):
    """示例API调用"""
    return requests.get("https://api.example.com", params=params)


'''


# 用于JSON日志的装饰器
def json_log(func: Callable) -> Callable:
    """
    记录函数调用的JSON格式日志装饰器
    """
    json_logger = get_logger("json")

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 准备函数调用信息
        call_info = {
            "function": func.__name__,
            "module": func.__module__,
            "args_count": len(args),
            "kwargs_count": len(kwargs),
            "timestamp": datetime.now().isoformat(),
        }

        # 记录函数开始执行
        json_logger.info(f"开始执行函数: {func.__name__}", extra={"call_info": call_info})

        start_time = time.time()
        try:
            # 执行原函数
            result = func(*args, **kwargs)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 记录成功执行信息
            json_logger.info(
                f"函数执行成功: {func.__name__}",
                extra={"call_info": call_info, "execution_time": execution_time, "result_type": type(result).__name__},
            )

            return result
        except Exception as e:
            # 计算执行时间
            execution_time = time.time() - start_time

            # 记录异常信息
            json_logger.error(
                f"函数执行异常: {func.__name__}",
                extra={
                    "call_info": call_info,
                    "execution_time": execution_time,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            # 重新抛出异常
            raise

    return wrapper


# ------------------------------ 整合 ---------------
def enhanced_logger(
    show_args: bool = True,  # 是否记录函数参数
    show_return: bool = True,  # 是否记录返回值
    time_threshold: float = 0.3,  # 执行时间阈值，超过此阈值将以警告级别记录
    context_key: str = None,  # 上下文信息的键名，如果提供，将尝试从第一个参数中获取此属性作为上下文
) -> Callable:
    """增强版函数调用日志

    :param show_args: 是否记录函数参数
    :param show_return: 是否记录返回值
    :param time_threshold: 执行时间阈值，超过此阈值将以警告级别记录
    :param context_key: 上下文信息的键名，如果提供，将尝试从第一个参数中获取此属性作为上下文
    :return: 装饰器
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 获取上下文信息
            context = None
            if context_key and args:
                context = getattr(args[0], context_key, None)

            extra = {context_key: context} if context else {}

            # 参数记录
            if show_args:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                logger.debug(f"调用函数 {func.__name__}({signature})", extra=extra)
            else:
                logger.debug(f"调用函数 {func.__name__}", extra=extra)

            # 记录开始时间
            start_time = time.perf_counter()

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 计算执行时间
                elapsed = time.perf_counter() - start_time

                # 根据阈值记录执行时间
                if elapsed > time_threshold:
                    logger.warning(f"{func.__name__} 执行耗时 {elapsed:.4f}秒 (阈值 {time_threshold}秒)", extra=extra)
                else:
                    logger.info(f"{func.__name__} 执行耗时 {elapsed:.4f}秒", extra=extra)

                # 返回值记录
                if show_return:
                    logger.debug(f"{func.__name__} 返回值类型: {type(result).__name__}, 值: {result!r}", extra=extra)
                else:
                    logger.debug(f"{func.__name__} 执行完成", extra=extra)

                return result

            except Exception as e:
                # 计算执行时间
                elapsed = time.perf_counter() - start_time

                # 记录异常信息，保留原始堆栈
                logger.exception(f"函数 {func.__name__} 执行异常，耗时 {elapsed:.4f}秒: {str(e)}", extra=extra)

                # 重新抛出异常，保留原始堆栈
                raise

        return wrapper

    return decorator
