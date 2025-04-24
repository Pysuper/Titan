"""
@Project ：Titan
@File    ：base.py
@Author  ：PySuper
@Date    ：2025/4/24 15:59
@Desc    ：Titan base.py
"""


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
