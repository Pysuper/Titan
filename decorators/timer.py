"""
@Project ：Titan
@File    ：timer.py
@Author  ：PySuper
@Date    ：2025/4/25 17:56
@Desc    ：Titan timer.py
"""

from logic.config import logger


# 测量执行时间
def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} 耗时: {end_time - start_time:.2f} 秒")
        return result

    return wrapper


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


@timer
@bar(desc="测试的进度条")
def main():
    total = 100
    yield total

    for i in range(total):
        yield
        time.sleep(0.05)

    return "我是函数的结果"


main()
