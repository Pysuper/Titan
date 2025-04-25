"""
@Project ：Titan
@File    ：class_.py
@Author  ：PySuper
@Date    ：2025/4/25 18:06
@Desc    ：Titan class_.py
"""


# 单例装饰器
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


"""

@singleton
class MyClass:
    def __init__(self, x):
        self.x = x
a = MyClass(1)
b = MyClass(2)
print(a is b)  #  输出  True，说明  a  和  b  是同一个实例

"""
