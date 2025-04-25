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
from typing import Callable, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def log_exception(func: Callable) -> Callable:
    """
    记录函数执行过程中的异常
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise

    return wrapper


def log_execution_time(func: Callable) -> Callable:
    """
    记录函数的执行时间
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} took {end_time - start_time:.2f} seconds to execute")
        return result

    return wrapper


def log_function_call(func: Callable) -> Callable:
    """
    记录函数的调用信息，包括参数和返回值
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logger.info(f"Calling {func.__name__}({signature})")
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} returned {result!r}")
        return result

    return wrapper


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


# 使用示例:
# @log_exception
# @log_execution_time
# @log_function_call
# def some_function(param1, param2):
#     # 函数实现
#     return result
#
# @debug
# def complex_data_processing(data, threshold=0.5):
#     # Your complex data processing code here
#     pass
