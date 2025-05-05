"""
@Project ：Backend
@File    ：cache.py
@Author  ：PySuper
@Date    ：2025/4/23 21:09
@Desc    ：缓存装饰器
"""

import time
from typing import Any, Callable


# 假设这里已经导入了Redis客户端
# from redis import Redis
# redis_client = Redis(host='localhost', port=6379, db=0)


# 缓存结果
def memoize(func):
    cache = {}

    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        cache[args] = result
        return result

    return wrapper


def cache_decorator(func):
    cache = dict()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


####### 也可以使用functools.lru_cache来实现缓存装饰器的效果
import functools


@functools.lru_cache(maxsize=None)
def example_function(x, y):
    """
    Python自带的缓存装饰器
    """
    return x + y


def memory_cache(expire_time: int = 60):
    """
    内存缓存装饰器

    :param expire_time: 缓存过期时间(秒),默认60秒
    :return: 装饰器函数
    """
    cache = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = str(args) + str(kwargs)
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < expire_time:
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result

        return wrapper

    return decorator


def redis_cache(expire_time: int = 60):
    """
    Redis缓存装饰器

    :param expire_time: 缓存过期时间(秒),默认60秒
    :return: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            result = redis_client.get(key)
            if result:
                return result
            result = func(*args, **kwargs)
            redis_client.setex(key, expire_time, result)
            return result

        return wrapper

    return decorator


# 使用示例:
# @memory_cache(expire_time=300)
# def some_expensive_function(param1, param2):
#     # 一些耗时的操作
#     return result

# @redis_cache(expire_time=3600)
# def another_expensive_function(param1, param2):
#     # 一些耗时的操作
#     return result
