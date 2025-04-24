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


# 使用示例:
# @log_exception
# @log_execution_time
# @log_function_call
# def some_function(param1, param2):
#     # 函数实现
#     return result
