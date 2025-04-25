"""
@Project ：Titan
@File    ：createMate.py
@Author  ：PySuper
@Date    ：2025/4/25 18:09
@Desc    ：Titan createMate.py
"""

# 元类使用
# https://mp.weixin.qq.com/s/lh7FnptwmXvuYwOOBiatog

# 协程使用
# https://mp.weixin.qq.com/s/a10vdeBZ2PXmeglfFkL9Lg

# Pottery是一个基于Redis的Python库，旨在简化分布式锁、集合和队列等操作。
# https://mp.weixin.qq.com/s/OUVgN2IU5ggx2NS34eVWnQ

# Ray 把计算任务分散到多台机器上运行，大大提升程序的执行效率
# https://mp.weixin.qq.com/s/bog7W93QPXhHqO-6eIM4Yg

# Pyro4 把那些分布在各处的资源、服务，统统封装成一个个对象
# https://mp.weixin.qq.com/s/_86XHnQR9xgQ0GYH09j-vw

# Celery：用 Python 实现分布式任务队列！
# https://mp.weixin.qq.com/s/TjF3VWFbEfnSiuhuY3XUSQ


# 创建多个相似但又不完全相同的类，那么可以通过一个函数来“定制”所需要的类，避免重复大量的样板代码
def create_class(class_name):
    class Class:
        def __init__(self, name, age):
            self.name = name
            self.age = age

        def greet(self):
            print(f"Hello, my name is {self.name} and I am {self.age} years old.")

    Class.__name__ = class_name
    return Class


Admin = create_class("Admin")
User = create_class("User")


# ----------------------------------
def create_class(class_name):
    return type(
        class_name,
        (object,),
        {
            "__init__": lambda self, name, age: setattr(self, "name", name) or setattr(self, "age", age),
            "greet": lambda self: f"Hello, my name is {self.name} and I am {self.age} years old.",
        },
    )


print(Admin("John Doe", 30).greet())
print(User("Jane Smith", 25).greet())
