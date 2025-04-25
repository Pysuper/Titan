"""
@Project ：Backend
@File    ：__init__.py.py
@Author  ：PySuper
@Date    ：2025/4/23 21:08
@Desc    ：Backend __init__.py.py
"""

from .cache import memory_cache, redis_cache
from .logs import log_exception, log_execution_time, log_function_call
from .request import send_to_url
from .save import save_result_to_file, save_output_to_file

# 保留被装饰函数的元数据
# 类装饰器
# 使用类作为装饰器
# 使用装饰器实现 权限校验

__all__ = [
    "memory_cache",
    "redis_cache",
    "log_exception",
    "log_execution_time",
    "log_function_call",
    "send_to_url",
    "save_result_to_file",
    "save_output_to_file",
]
