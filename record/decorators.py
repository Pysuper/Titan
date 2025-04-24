"""
@Project ：Titan
@File    ：all.py
@Author  ：PySuper
@Date    ：2025/4/24 14:58
@Desc    ：Titan all.py
"""

import time
import functools
from functools import wraps
from loguru import logger


# 测量执行时间
def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} 耗时: {end_time - start_time:.2f} 秒")
        return result

    return wrapper


@timer
def my_data_processing_function():
    pass


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


@memoize
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


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


@validate_input
def analyze_data(data):
    pass


# 日志输出
def log_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        with open("results.log", "a") as log_file:
            log_file.write(f"{func.__name__} - Result: {result}\n")
        return result

    return wrapper


@log_results
def calculate_metrics(data):
    pass


# 优雅的错误处理
def suppress_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            return None

    return wrapper


@suppress_errors
def preprocess_data(data):
    # Your data preprocessing code here
    pass


# 确保质量结果
def validate_output(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if valid_output(result):
            return result
        else:
            raise ValueError("Invalid output. Please check your function logic.")

    return wrapper


@validate_output
def clean_data(data):
    pass


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


@retry(max_attempts=3, delay=2)
def fetch_data_from_api(api_url):
    pass


# 调试变得更容易
def debug(func):
    def wrapper(*args, **kwargs):
        print(f"Debugging {func.__name__} - args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper


@debug
def complex_data_processing(data, threshold=0.5):
    # Your complex data processing code here
    pass


import warnings


# 处理废弃的函数
def deprecated(func):
    def wrapper(*args, **kwargs):
        warnings.warn(f"{func.__name__} is deprecated and will be removed in future versions.", DeprecationWarning)
        return func(*args, **kwargs)

    return wrapper


@deprecated
def old_data_processing(data):
    # Your old data processing code here
    pass


"""
import matplotlib.pyplot as plt

# 漂亮的可视化
def visualize_results(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        plt.figure()
        # Your visualization code here
        plt.show()
        return result
    return wrapper

@visualize_results
def analyze_and_visualize(data):
    # Your combined analysis and visualization code here
    pass

"""


# ------------------------------


def valid_output(result):
    pass


# ------------------------ 日志装饰器

import logging


def log_decorator(func):
    def wrapper(*args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        logging.info(f"开始执行 {func.__name__} 函数")
        result = func(*args, **kwargs)
        logging.info(f"{func.__name__} 函数执行完毕")
        return result

    return wrapper


@log_decorator
def example_function():
    print("示例函数执行中...")


example_function()

# ------------------------ 缓存装饰器


def cache_decorator(func):
    cache = dict()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


@cache_decorator
def example_function(x, y):
    return x + y


print(example_function(1, 2))  # 输出 3，计算并缓存结果
print(example_function(1, 2))  # 输出 3，从缓存中获取结果

####### 也可以使用functools.lru_cache来实现缓存装饰器的效果
import functools


@functools.lru_cache(maxsize=None)
def example_function(x, y):
    return x + y


print(example_function(1, 2))  # 输出 3，计算并缓存结果
print(example_function(1, 2))  # 输出 3，从缓存中获取结果

# ------------------------ 类型检查装饰器


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


# 使用装饰器进行类型检查
@type_check
def add(a: int, b: int) -> int:
    return a + b


print(add(1, 2))  # 输出 3
# print(add("1", "2"))  # 抛出 TypeError，因为参数类型不正确


# ------------------------ 单例装饰器
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton
class MyClass:
    def __init__(self, x):
        self.x = x


a = MyClass(1)
b = MyClass(2)
print(a is b)  #  输出  True，说明  a  和  b  是同一个实例


# ------------------------ 重试装饰器


def retry(retries=3, delay=1):
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


@retry(retries=5, delay=2)
def my_function():
    #  这里是你的函数实现
    pass


# ------------------------ 性能度量器
import cProfile
from functools import wraps


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


@performance_metric
def my_function():
    #  这里是你的函数实现
    pass


# ------------------------ 进度条
import time
from tqdm import trange


def bar(desc="", unit="it"):
    def decorator(func):
        def inner(*args, **kwargs):
            pbar = None

            gen = func(*args, **kwargs)

            try:
                while True:
                    i = next(gen)
                    if pbar is None:
                        pbar = trange(i, desc=desc, unit=unit)

                    pbar.update(1)
            except StopIteration as e:
                pbar.close()

                return e.value

        return inner

    return decorator


@bar(desc="测试的进度条")
def main():
    total = 100
    yield total

    for i in range(total):
        yield
        time.sleep(0.05)

    return "我是函数的结果"


if __name__ == "__main__":
    result = main()
    print(result)

# 保留被装饰函数的元数据
# 类装饰器
# 使用类作为装饰器
# 使用装饰器实现 权限校验
