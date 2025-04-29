"""
@Project ：Titan
@File    ：scheduler.py
@Author  ：PySuper
@Date    ：2025/4/24 14:03
@Desc    ：Titan scheduler.py
"""

import logging
import os
import sys
from typing import Any, Dict

from celery import Celery
from celery.result import AsyncResult
from celery.schedules import crontab

# 将项目根目录添加到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
try:
    from config.task import CELERY_CONFIG
    from config.mq import BROKER_URL, BACKEND_URL, CELERY_QUEUES
except ImportError:
    # 如果无法导入配置，使用默认值
    CELERY_CONFIG = {}
    BROKER_URL = "redis://localhost:6379/0"
    BACKEND_URL = "redis://localhost:6379/1"
    CELERY_QUEUES = {}


class CeleryScheduler:
    """
    基于Celery的分布式任务调度器
    """

    def __init__(self, app_name: str = "titan", broker: str = None, backend: str = None, config: Dict[str, Any] = None):
        """
        初始化Celery调度器

        Args:
            app_name: Celery应用名称
            broker: 消息代理地址，默认使用配置文件中的值
            backend: 结果存储后端，默认使用配置文件中的值
            config: 自定义配置，会覆盖默认配置
        """
        # 使用传入参数或配置文件中的设置
        self.broker = broker or BROKER_URL
        self.backend = backend or BACKEND_URL
        self.app = Celery(app_name, broker=self.broker, backend=self.backend)
        self.logger = logging.getLogger(__name__)

        # 合并配置
        self.config = CELERY_CONFIG.copy()
        if config:
            self.config.update(config)

        self._configure_app()

    def _configure_app(self) -> None:
        """配置Celery应用"""
        # 应用配置
        self.app.conf.update(self.config)

        # 如果有队列配置，设置队列
        if CELERY_QUEUES:
            self.app.conf.task_queues = CELERY_QUEUES

    def register_task(self, task_func):
        """
        注册Celery任务

        Args:
            task_func: 要注册为Celery任务的函数

        Returns:
            装饰后的任务函数
        """
        return self.app.task(task_func)

    def schedule_task(
        self, task, args=None, kwargs=None, countdown=None, eta=None, queue="default", priority=None
    ) -> AsyncResult:
        """
        调度任务异步执行

        Args:
            task: 要执行的任务函数(已用app.task装饰)
            args: 位置参数列表
            kwargs: 关键字参数字典
            countdown: 延迟执行的秒数
            eta: 指定执行时间点(datetime对象)
            queue: 要使用的队列名称
            priority: 任务优先级(0-9，9为最高优先级)

        Returns:
            AsyncResult对象，可用于追踪任务状态
        """
        args = args or []
        kwargs = kwargs or {}

        task_options = {
            "countdown": countdown,
            "eta": eta,
            "queue": queue,
        }

        # 如果设置了优先级，添加到选项中
        if priority is not None:
            task_options["priority"] = priority

        # 移除None值的选项
        task_options = {k: v for k, v in task_options.items() if v is not None}

        result = task.apply_async(args=args, kwargs=kwargs, **task_options)
        self.logger.info(f"任务已调度: {task.__name__}, 任务ID: {result.id}, 队列: {queue}")
        return result

    def schedule_periodic_task(
        self, task_name: str, task, schedule, args=None, kwargs=None, queue="default", priority=None
    ) -> None:
        """
        添加周期性任务到定时任务表

        Args:
            task_name: 任务名称，作为定时任务的唯一标识
            task: 要执行的任务函数(已用app.task装饰)
            schedule: 调度时间，可以是数字(表示秒数)或crontab表达式
            args: 位置参数列表
            kwargs: 关键字参数字典
            queue: 要使用的队列名称
            priority: 任务优先级(0-9，9为最高优先级)
        """
        args = args or []
        kwargs = kwargs or {}

        # 更新定时任务表
        self.app.conf.beat_schedule = self.app.conf.beat_schedule or {}

        task_config = {
            "task": task.name,
            "schedule": schedule,
            "args": args,
            "kwargs": kwargs,
            "options": {"queue": queue},
        }

        # 如果设置了优先级，添加到选项中
        if priority is not None:
            task_config["options"]["priority"] = priority

        self.app.conf.beat_schedule[task_name] = task_config
        self.logger.info(f"周期性任务已添加: {task_name}, 任务: {task.name}, 队列: {queue}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            包含任务状态信息的字典
        """
        result = AsyncResult(task_id, app=self.app)
        status = {
            "id": task_id,
            "status": result.status,
            "successful": result.successful(),
            "failed": result.failed(),
        }

        if result.ready():
            try:
                status["result"] = result.get(timeout=1)
            except Exception as e:
                status["error"] = str(e)

        return status

    def cancel_task(self, task_id: str) -> bool:
        """
        取消正在等待的任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        try:
            self.app.control.revoke(task_id, terminate=True)
            self.logger.info(f"任务已取消: {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
            return False

    def create_crontab(self, minute="*", hour="*", day_of_week="*", day_of_month="*", month_of_year="*") -> crontab:
        """
        创建crontab表达式

        Args:
            minute: 分钟 (0-59)
            hour: 小时 (0-23)
            day_of_week: 星期几 (0-6 或 mon,tue,wed,thu,fri,sat,sun)
            day_of_month: 每月第几天 (1-31)
            month_of_year: 月份 (1-12 或 jan,feb,mar,apr,...)

        Returns:
            crontab对象
        """
        return crontab(
            minute=minute, hour=hour, day_of_week=day_of_week, day_of_month=day_of_month, month_of_year=month_of_year
        )

    def start_worker(self, queues=None, concurrency=4, loglevel="INFO"):
        """
        启动Celery worker

        Args:
            queues: 要监听的队列列表
            concurrency: 并发worker数
            loglevel: 日志级别
        """
        argv = ["worker", f"--concurrency={concurrency}", f"--loglevel={loglevel}"]

        if queues:
            queue_str = ",".join(queues)
            argv.extend(["-Q", queue_str])

        self.app.worker_main(argv)

    def start_beat(self, loglevel="INFO"):
        """
        启动Celery beat（定时任务调度器）

        Args:
            loglevel: 日志级别
        """
        argv = ["beat", f"--loglevel={loglevel}"]
        self.app.start(argv)
