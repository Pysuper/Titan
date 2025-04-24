"""
@Project ：Titan
@File    ：my_test.py
@Author  ：PySuper
@Date    ：2025/4/24 16:07
@Desc    ：Titan my_test.py
"""

import cProfile
import logging
import time
import warnings
from functools import wraps

import matplotlib.pyplot as plt
from loguru import logger


# 测量执行时间
def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        # logger.info(f"{func.__name__} 耗时: {end_time - start_time:.2f} 秒")
        logger.info(f"{func.__name__} 耗时: {end_time - start_time:.9f} 秒")
        return result

    return wrapper


# 缓存结果，也可以直接使用 from functools import lru_cache  @lru_cache(maxsize=None)
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

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


# 数据验证
def validate_input(func):
    def wrapper(*args, **kwargs):
        # Your data validation logic here
        valid_data = None
        if valid_data:
            return func(*args, **kwargs)
        else:
            raise ValueError("Invalid data. Please check your inputs.")

    return wrapper


# 过程日志
def log_decorator(func):
    def wrapper(*args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        logging.info(f"开始执行 {func.__name__} 函数")
        result = func(*args, **kwargs)
        logging.info(f"{func.__name__} 函数执行完毕")
        return result

    return wrapper


# 结果日志
def log_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        with open(f"{func.__name__}_result.log", "a") as log_file:
            log_file.write(f"{func.__name__} result: {result}\n")
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


# 确保质量结果
def validate_output(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # 定义一个校验结果的函数
        # if valid_output(result):
        if result is not None:
            return result
        else:
            raise ValueError("Invalid output. Please check your function logic.")

    return wrapper


# 重试执行
def retry(max_attempts, delay):
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"第 {attempts + 1} 次尝试失败：{e}， {delay} 秒后重试...")
                    attempts += 1
                    time.sleep(delay)
            raise Exception("已达到最大尝试次数。")

        return wrapper

    return decorator


# 调试变得更容易
def debug(func):
    def wrapper(*args, **kwargs):
        logger.debug(f"{func.__name__} - args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper


# 处理废弃的函数
def deprecated(func):
    def wrapper(*args, **kwargs):
        warnings.warn(f"{func.__name__} is deprecated and will be removed in future versions.", DeprecationWarning)
        return func(*args, **kwargs)

    return wrapper


# 漂亮的可视化
def visualize_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        plt.figure()
        # Your visualization code here
        plt.show()
        return result

    return wrapper


# 类型检查装饰器
def type_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 获取函数的参数注解
        annotations = func.__annotations__

        # 遍历参数和注解，检查类型是否正确
        for arg, annotation in zip(args, annotations.values()):
            if not isinstance(arg, annotation):
                raise TypeError(f"参数 {arg} 的类型应为 {annotation}，但实际类型为 {type(arg)}")

        # 调用原始函数
        return func(*args, **kwargs)

    return wrapper


# 单例装饰器
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


# 性能度量器
def performance_metric(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        profiler.print_stats()
        return result

    return wrapper


# -----------------------------------------------------------------------#


@timer  # ...从下往上，从内往外...
# @memoize
# @log_results
# @suppress_errors
# @retry(max_attempts=3, delay=2)
# @debug
# @deprecated
# @visualize_results  # 自动可视化结果
# @log_decorator # 可以和log_results 写到一起
# @cache_decorator  # 也是缓存装饰器，看看和memoize的区别
# @type_check  # 类型检查装饰器
@performance_metric
def factorial(a: int, b: int) -> int:
    return a + b


@singleton
class MyClass:
    def __init__(self, x):
        self.x = x


if __name__ == "__main__":
    # a = MyClass(1)
    # b = MyClass(2)
    # print(a is b)  #  输出  True，说明  a  和  b  是同一个实例
    result = factorial(12312312123213123323, 12)
    print(result)
