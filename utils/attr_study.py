"""
@Project ：Titan
@File    ：dataclass_.py
@Author  ：PySuper
@Date    ：2025/4/24 15:19
@Desc    ：Titan dataclass_.py
"""

import attr

# https://mp.weixin.qq.com/s/uX2rn8ndXVIFN6Nm88Kh4Q


@attr.s
class Person:
    """
    @attr.s装饰器替代了传统的__init__方法
    而attr.ib()用于声明类的属性及其类型注解
    这样的定义方式使得代码更简洁 ，同时保留了静态类型检查的好处

    @attr.s是attrs库中最核心的装饰器，它能够自动为类生成构造函数、getter和setter方法，以及__repr__、__eq__等特殊方法。
    """

    name: str = attr.ib()
    age: int = attr.ib()


# 创建Person实例
person_instance = Person("Alice", 30)

# 访问属性
print(person_instance.name)  # 输出: Alice
print(person_instance.age)  # 输出: 30


# -------------------------------------------------------------------------------
@attr.s
class Book:
    title: str = attr.ib()
    author: str = attr.ib()
    year: int = attr.ib()


# 创建Book实例
book = Book("The Great Gatsby", "F. Scott Fitzgerald", 1925)

# 输出Book实例的信息
print(book)


# -------------------------------------------------------------------------------
@attr.s
class Book:
    title: str = attr.ib(default="Unknown Title")
    author: str = attr.ib(default="Unknown Author")
    year: int = attr.ib(default=0)
    _is_bestseller: bool = attr.ib(init=False, default=False)


# 创建Book实例，不需传入所有参数
book = Book()

# 修改可变属性
book.title = "The Catcher in the Rye"
book.author = "J.D. Salinger"
book.year = 1951

# 尝试修改不可变属性
try:
    book._is_bestseller = True
except AttributeError as e:
    print(e)  # 输出: can't set attribute

# 输出Book实例的信息
print(book)  # 输出: Book(title='The Catcher in the Rye', author='J.D. Salinger', year=1951)


# -------------------------------------------------------------------------------
@attr.s
class User:
    """
    使用@attr.validate装饰器在attrs库中，数据验证是一个重要功能，它帮助确保类的属性值满足预期条件。通过@attr.validate装饰器 ，可以在属性设置前后执行自定义的验证逻辑。
    """

    age: int = attr.ib()


# TODO：@age.validator
def check_age(self, attribute, value):
    if not (0 < value <= 150):
        raise ValueError("Age must be between 0 and 150.")


# 尝试创建User实例，验证年龄
try:
    user = User(age=151)
except ValueError as e:
    print(e)  # 输出: Age must be between 0 and 150.


# ---------------------------------------------------------------------
@attr.s
class BankAccount:
    """
    对多个属性间的依赖关系进行验证
    validate_account方法作为全局验证器 ，检查账户余额是否在透支限额内。如果余额低于允许的透支限制，就抛出异常。
    """

    balance: float = attr.ib()
    overdraft_limit: float = attr.ib()

    @attr.s.validator
    def validate_account(self, attributes, values):
        if "balance" in values and "overdraft_limit" in values:
            if values["balance"] < 0 and abs(values["balance"]) > values["overdraft_limit"]:
                raise ValueError("Balance is below the allowed overdraft limit.")


# 测试验证逻辑
try:
    account = BankAccount(balance=-200, overdraft_limit=100)
except ValueError as e:
    print(e)  # 输出: Balance is below the allowed overdraft limit.

# ---------------------------------------------------------------------
import json
import attr


@attr.s(auto_attribs=True)
class Person:
    name: str = attr.ib()
    age: int = attr.ib()
    address: dict = attr.ib()


#  创建Person实例
person = Person(name="John  Doe", age=30, address={"street": "123  Elm  St", "city": "Springfield"})

#  序列化为JSON字符串
person_json = json.dumps(attr.asdict(person))

#  输出JSON字符串
print(
    person_json
)  #  输出:  {"name":  "John  Doe",  "age":  30,  "address":  {"street":  "123  Elm  St",  "city":  "Springfield"}}


@attr.s(auto_attribs=True)
class Person:
    name: str = attr.ib()
    age: int = attr.ib()
    address: dict = attr.ib()


#  JSON字符串
person_json = '{"name":  "Jane  Doe",  "age":  28,  "address":  {"street":  "456  Maple  St",  "city":  "Springfield"}}'

#  反序列化为字典
person_dict = json.loads(person_json)

#  映射回Person类
person = attr.evolve(Person(**person_dict))

#  输出Person实例
print(
    person
)  #  输出:  Person(name='Jane  Doe',  age=28,  address={'street':  '456  Maple  St',  'city':  'Springfield'})


# ---------------------------------------------------------------------  attr与dataclasses的比较与转换
from dataclasses import dataclass, asdict
import attr


@attr.s(auto_attribs=True)
class PersonAttr:
    name: str
    age: int


@dataclass
class PersonDataclass:
    name: str
    age: int


#  attr实例转dataclass
person_attr = PersonAttr("Alice", 30)
person_dataclass = PersonDataclass(**asdict(person_attr))

#  dataclass实例转attr
person_dataclass = PersonDataclass("Bob", 25)
person_attr = PersonAttr(**dataclass.asdict(person_dataclass))

print(person_dataclass)  #  输出:  PersonDataclass(name='Alice',  age=30)
print(person_attr)  #  输出:  PersonAttr(name='Bob',  age=25)

# ------------------------------------------------------------------------- attr与Pydantic的协同工作
from pydantic import BaseModel
import attr


@attr.s(auto_attribs=True)
class UserAttr:
    username: str
    email: str


class UserPydantic(BaseModel):
    username: str
    email: str


#  attr转Pydantic
user_attr = UserAttr("john_doe", "john.doe@example.com")
user_pydantic = UserPydantic(**attr.asdict(user_attr))

#  Pydantic转attr
user_pydantic = UserPydantic(username="jane_smith", email="jane.smith@example.com")
user_attr = UserAttr(**user_pydantic.dict())

print(user_pydantic)  #  输出:  username='john_doe'  email='john.doe@example.com'
print(user_attr)  #  输出:  UserAttr(username='jane_smith',  email='jane.smith@example.com')


# ---------------------------------------------------------------------  性能优化
# https://mp.weixin.qq.com/s/uX2rn8ndXVIFN6Nm88Kh4Q
# 通过设置auto_attribs=True，可以让属性的类型注解同时作为实例变量的类型提示和自动赋值的基础 ，减少不必要的属性初始化开销
@attr.s(auto_attribs=True)
class MyClass:
    value: int
