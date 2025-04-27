"""
@Project ：Backend
@File    ：save.py
@Author  ：PySuper
@Date    ：2025/4/23 21:09
@Desc    ：IO保存装饰器
"""

import functools
import sys
from io import StringIO
from typing import Callable, Any


def save_result_to_file(filename: str):
    """
    将函数返回结果保存到文件的装饰器

    @param filename: 保存结果的文件名
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(str(result))
            return result

        return wrapper

    return decorator


def save_output_to_file(filename: str):
    """
    将函数执行过程中的输出保存到文件的装饰器

    @param filename: 保存输出的文件名
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 重定向标准输出到StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                result = func(*args, **kwargs)
                output = sys.stdout.getvalue()
            finally:
                # 恢复标准输出
                sys.stdout = old_stdout

            # 将捕获的输出写入文件
            with open(filename, "w", encoding="utf-8") as f:
                f.write(output)

            return result

        return wrapper

    return decorator


# 使用示例:
# @save_result_to_file('result.txt')
# def some_function(param1, param2):
#     # 函数实现
#     return result

# @save_output_to_file('output.log')
# def another_function(param1, param2):
#     print("This will be saved to the file")
#     # 函数实现
#     return result
