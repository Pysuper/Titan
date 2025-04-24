"""
@Project ：Titan
@File    ：dataclass_order.py
@Author  ：PySuper
@Date    ：2025/4/24 15:58
@Desc    ：Titan dataclass_order.py
"""

from dataclasses import dataclass


@dataclass(order=True)
class Student:
    score: int
    name: str


# 创建Student对象
student1 = Student(85, "Alice")
student2 = Student(90, "Bob")
student3 = Student(80, "Charlie")

# 比较大小
print(student1 > student3)  # 输出: True
print(student2 < student1)  # 输出: False

# 排序
students = [student1, student2, student3]
students.sort()  # 默认按照 score 排序

print(students)
# 输出：[Student(score=80, name='Charlie'), Student(score=85, name='Alice'), Student(score=90, name='Bob')]
