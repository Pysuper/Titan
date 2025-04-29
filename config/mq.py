"""
@Project ：Backend
@File    ：mq.py
@Author  ：PySuper
@Date    ：2025/4/24 09:53
@Desc    ：消息队列配置
"""

# Redis配置
REDIS_CONFIG = {
    'default': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
        'max_connections': 100,
    },
    'result_backend': {
        'host': 'localhost',
        'port': 6379,
        'db': 1,
        'password': None,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
    },
    'cache': {
        'host': 'localhost',
        'port': 6379,
        'db': 2,
        'password': None,
        'socket_timeout': 3,
        'socket_connect_timeout': 3,
        'retry_on_timeout': True,
    }
}

# Celery Broker URL格式
def get_broker_url(config_name='default'):
    """
    根据配置名称获取Broker URL

    Args:
        config_name: Redis配置名称，默认为'default'

    Returns:
        Broker URL字符串
    """
    config = REDIS_CONFIG.get(config_name, REDIS_CONFIG['default'])
    password_part = f":{config['password']}@" if config.get('password') else ""
    return f"redis://{password_part}{config['host']}:{config['port']}/{config['db']}"

# Celery Result Backend URL格式
def get_backend_url(config_name='result_backend'):
    """
    根据配置名称获取Result Backend URL

    Args:
        config_name: Redis配置名称，默认为'result_backend'

    Returns:
        Backend URL字符串
    """
    return get_broker_url(config_name)

# 默认Broker和Backend URL
BROKER_URL = get_broker_url()
BACKEND_URL = get_backend_url()

# 队列定义
CELERY_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
        'queue_arguments': {'x-max-priority': 10}
    },
    'high_priority': {
        'exchange': 'high_priority',
        'routing_key': 'high_priority',
        'queue_arguments': {'x-max-priority': 10}
    },
    'low_priority': {
        'exchange': 'low_priority',
        'routing_key': 'low_priority',
        'queue_arguments': {'x-max-priority': 10}
    },
}
