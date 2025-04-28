"""
@Project ：Backend
@File    ：task.py
@Author  ：PySuper
@Date    ：2025/4/24 09:53
@Desc    ：Celery 任务配置
"""
from datetime import timedelta


# Celery任务配置
CELERY_CONFIG = {
    # 序列化配置
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',

    # 时区配置
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,

    # 任务执行配置
    'task_track_started': True,
    'worker_max_tasks_per_child': 200,
    'task_acks_late': True,
    'worker_prefetch_multiplier': 1,

    # 结果配置
    'result_expires': timedelta(days=1),
    'task_ignore_result': False,

    # 任务重试配置
    'task_default_retry_delay': 180,  # 默认重试延迟秒数
    'task_max_retries': 3,  # 最大重试次数

    # 任务限速配置
    'task_default_rate_limit': '10/m',  # 默认限速（每分钟10个任务）

    # 日志配置
    'worker_log_format': "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    'worker_task_log_format': "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",

    # 队列配置
    'task_queues': {
        'default': {'exchange': 'default', 'routing_key': 'default'},
        'high_priority': {'exchange': 'high_priority', 'routing_key': 'high_priority'},
        'low_priority': {'exchange': 'low_priority', 'routing_key': 'low_priority'},
    },
    'task_default_queue': 'default',
    'task_default_exchange': 'default',
    'task_default_routing_key': 'default',

    # 定时任务配置
    'beat_schedule': {},
}
