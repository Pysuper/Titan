"""
@Project ：Titan
@File    ：class_.py
@Author  ：PySuper
@Date    ：2025/4/25 18:06
@Desc    ：Titan class_.py
"""

import functools
import inspect
import threading
import time


# 单例装饰器
def singleton(cls):
    """
    单例装饰器，确保在整个程序中只创建一个实例
    """
    instances = {}

    def get_instance(*args, **kwargs):
        """
        获取单例实例
        """
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


# 线程安全的单例装饰器
def thread_safe_singleton(cls):
    """
    线程安全的单例装饰器，确保在多线程环境下也只创建一个实例
    """
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:  # 双重检查锁定模式
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


# 类属性验证装饰器
def validate_attributes(**validators):
    """
    为类属性添加验证规则的装饰器

    示例:
    @validate_attributes(
        name=lambda x: isinstance(x, str) and len(x) > 0,
        age=lambda x: isinstance(x, int) and x >= 0
    )
    class Person:
        def __init__(self, name, age):
            self.name = name
            self.age = age
    """

    def decorator(cls):
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)

            for attr_name, validator in validators.items():
                if hasattr(self, attr_name):
                    value = getattr(self, attr_name)
                    if not validator(value):
                        raise ValueError(f"属性 {attr_name} 的值 {value} 验证失败")

        cls.__init__ = new_init
        return cls

    return decorator


# 自动记录类方法调用的装饰器
def log_methods(cls):
    """
    自动为类的所有方法添加日志记录
    """
    from loguru import logger

    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("__"):  # 跳过魔术方法

            @functools.wraps(method)
            def wrapper(self, *args, method=method, name=name, **kwargs):
                logger.debug(f"调用 {cls.__name__}.{name} 方法")
                result = method(self, *args, **kwargs)
                logger.debug(f"{cls.__name__}.{name} 方法返回: {result}")
                return result

            setattr(cls, name, wrapper)

    return cls


# 类方法性能监控装饰器
def profile_methods(cls):
    """
    为类的所有方法添加性能监控
    """
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("__"):  # 跳过魔术方法

            @functools.wraps(method)
            def wrapper(self, *args, method=method, name=name, **kwargs):
                start_time = time.time()
                result = method(self, *args, **kwargs)
                end_time = time.time()
                print(f"{cls.__name__}.{name} 执行时间: {end_time - start_time:.6f}秒")
                return result

            setattr(cls, name, wrapper)

    return cls


# 自动注册子类装饰器
def auto_register(base_cls):
    """
    自动将所有子类注册到基类的registry属性中

    示例:
    @auto_register
    class Plugin:
        registry = []

    class MyPlugin(Plugin):
        pass  # 自动注册到 Plugin.registry
    """
    original_init_subclass = base_cls.__init_subclass__

    @classmethod
    def new_init_subclass(cls, **kwargs):
        if hasattr(original_init_subclass, "__func__"):
            original_init_subclass.__func__(cls, **kwargs)
        else:
            original_init_subclass(cls, **kwargs)

        if not hasattr(base_cls, "registry"):
            base_cls.registry = []

        base_cls.registry.append(cls)

    base_cls.__init_subclass__ = new_init_subclass
    return base_cls


# 不可变类装饰器
def immutable(cls):
    """
    使类的实例在初始化后不可修改
    """
    original_setattr = cls.__setattr__

    def __setattr__(self, key, value):
        if hasattr(self, "_initialized") and self._initialized:
            raise AttributeError(f"无法修改不可变类 {cls.__name__} 的属性")
        original_setattr(self, key, value)

    original_init = cls.__init__

    @functools.wraps(original_init)
    def __init__(self, *args, **kwargs):
        self._initialized = False
        original_init(self, *args, **kwargs)
        self._initialized = True

    cls.__setattr__ = __setattr__
    cls.__init__ = __init__
    return cls


# 自动属性装饰器
def auto_properties(cls):
    """
    自动为类的所有_开头的属性创建property

    示例:
    @auto_properties
    class Person:
        def __init__(self, name, age):
            self._name = name
            self._age = age

    # 自动创建 name 和 age 属性
    """
    for key in list(cls.__dict__.keys()):
        if key.startswith("_") and not key.startswith("__"):
            prop_name = key[1:]  # 去掉前导下划线

            if not hasattr(cls, prop_name):
                # 创建getter
                def getter(self, key=key):
                    return getattr(self, key)

                # 创建setter
                def setter(self, value, key=key):
                    setattr(self, key, value)

                # 设置property
                setattr(cls, prop_name, property(getter, setter))

    return cls


# 依赖注入装饰器
def inject_dependencies(cls):
    """
    简单的依赖注入装饰器，自动注入类所需的依赖

    示例:
    class Database:
        def query(self):
            return "数据"

    @inject_dependencies
    class UserService:
        database: Database

        def get_user(self):
            return self.database.query()
    """
    original_init = cls.__init__

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        # 查找类型注解
        annotations = getattr(cls, "__annotations__", {})

        # 为每个注解创建实例并注入
        for attr_name, attr_type in annotations.items():
            if not attr_name.startswith("__") and attr_name not in kwargs:
                try:
                    setattr(self, attr_name, attr_type())
                except Exception as e:
                    print(f"无法注入依赖 {attr_name}: {e}")

        original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls


# 缓存类方法结果的装饰器
def cache_methods(cls):
    """
    为类的所有方法添加结果缓存
    """
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("__"):  # 跳过魔术方法
            setattr(cls, name, functools.lru_cache(maxsize=128)(method))

    return cls


"""

# 使用示例

# 单例模式
@singleton
class MyClass:
    def __init__(self, x):
        self.x = x
a = MyClass(1)
b = MyClass(2)
print(a is b)  #  输出  True，说明  a  和  b  是同一个实例

# 线程安全单例
@thread_safe_singleton
class ThreadSafeClass:
    def __init__(self, value):
        self.value = value

# 属性验证
@validate_attributes(
    name=lambda x: isinstance(x, str) and len(x) > 0,
    age=lambda x: isinstance(x, int) and x >= 0
)
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

# 方法日志记录
@log_methods
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

# 性能监控
@profile_methods
class SlowCalculator:
    def complex_calculation(self, n):
        time.sleep(0.1)  # 模拟耗时操作
        return n * n

# 自动注册子类
@auto_register
class Plugin:
    registry = []

    def run(self):
        pass

class VideoPlugin(Plugin):
    def run(self):
        return "处理视频"

class AudioPlugin(Plugin):
    def run(self):
        return "处理音频"

# 使用注册的插件
for plugin_cls in Plugin.registry:
    plugin = plugin_cls()
    print(plugin.run())

# 不可变类
@immutable
class Config:
    def __init__(self, host, port):
        self.host = host
        self.port = port

# 自动属性
@auto_properties
class User:
    def __init__(self, username, email):
        self._username = username
        self._email = email

# 依赖注入
class Logger:
    def log(self, message):
        print(f"日志: {message}")

class Database:
    def query(self):
        return "数据库结果"

@inject_dependencies
class UserService:
    logger: Logger
    database: Database

    def get_user(self):
        self.logger.log("获取用户")
        return self.database.query()

# 缓存方法结果
@cache_methods
class ExpensiveCalculator:
    def fibonacci(self, n):
        if n <= 1:
            return n
        return self.fibonacci(n-1) + self.fibonacci(n-2)

"""
