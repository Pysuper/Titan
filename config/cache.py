"""
@Project ：Backend
@File    ：cache.py
@Author  ：PySuper
@Date    ：2025/4/24 09:55
@Desc    ：Backend cache.py
"""
from datetime import timedelta
from redis import Redis
from flask_caching import Cache

# Redis缓存配置
REDIS_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
    'CACHE_DEFAULT_TIMEOUT': 300,  # 默认缓存时间300秒
    'CACHE_KEY_PREFIX': 'titan_cache_'
}

# 内存缓存配置
MEMORY_CONFIG = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 60  # 默认缓存时间60秒
}

# 初始化缓存实例
cache = Cache()

def init_cache(app, config_type='redis'):
    """
    初始化缓存配置
    :param app: Flask应用实例
    :param config_type: 缓存类型，可选 'redis' 或 'memory'
    """
    if config_type == 'redis':
        app.config.from_mapping(REDIS_CONFIG)
    else:
        app.config.from_mapping(MEMORY_CONFIG)

    cache.init_app(app)

def get_cache_key(prefix, *args):
    """
    生成缓存key
    :param prefix: 缓存前缀
    :param args: 其他参数
    :return: 生成的缓存key
    """
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def cache_response(timeout=300):
    """
    缓存响应装饰器
    :param timeout: 缓存时间，单位秒
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            cache_key = get_cache_key(f.__name__, *args, *tuple(kwargs.values()))
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        return wrapper
    return decorator
