"""
@Project ：Titan
@File    ：celery_example.py
@Author  ：PySuper
@Date    ：2025/4/24 14:30
@Desc    ：Celery调度器使用示例
"""

import os
import sys
import time
from datetime import datetime, timedelta

from loguru import logger

# 将项目根目录添加到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from scheduler import CeleryScheduler


# 创建调度器实例（使用配置文件中的设置）
scheduler = CeleryScheduler(app_name="titan")

# 或者指定自定义配置
# scheduler = CeleryScheduler(
#     app_name='titan',
#     broker=BROKER_URL,
#     backend=BACKEND_URL,
#     config={
#         'worker_max_tasks_per_child': 100,
#         'task_default_rate_limit': '20/m',
#     }
# )


# 定义任务函数
@scheduler.register_task
def add(x, y):
    """简单的加法任务"""
    logger.info(f"执行加法任务: {x} + {y}")
    time.sleep(2)  # 模拟耗时操作
    return x + y


@scheduler.register_task
def process_data(data_id):
    """处理数据任务"""
    logger.info(f"开始处理数据: {data_id}")
    time.sleep(5)  # 模拟耗时操作
    result = f"数据{data_id}处理完成"
    logger.info(result)
    return result


def example_one_time_task():
    """演示一次性任务调度"""
    # 立即执行任务
    result1 = scheduler.schedule_task(add, args=[10, 20])
    logger.info(f"任务ID: {result1.id}")

    # 延迟5秒执行任务
    result2 = scheduler.schedule_task(add, args=[5, 8], countdown=5)
    logger.info(f"延迟任务ID: {result2.id}")

    # 在指定时间执行任务
    eta = datetime.now() + timedelta(seconds=10)
    result3 = scheduler.schedule_task(process_data, kwargs={"data_id": "DATA_001"}, eta=eta)
    logger.info(f"定时任务ID: {result3.id}, 执行时间: {eta}")

    # 使用高优先级队列执行任务
    result4 = scheduler.schedule_task(
        process_data, kwargs={"data_id": "PRIORITY_DATA"}, queue="high_priority", priority=9
    )
    logger.info(f"高优先级任务ID: {result4.id}, 队列: high_priority")

    # 等待并获取任务结果
    task_ids = [result1.id, result2.id, result3.id, result4.id]

    # 等待任务完成并查看结果
    time.sleep(15)
    for task_id in task_ids:
        status = scheduler.get_task_status(task_id)
        logger.info(f"任务状态: {status}")


def example_periodic_tasks():
    """演示周期性任务调度"""
    # 每30秒执行一次
    scheduler.schedule_periodic_task(task_name="add-every-30-seconds", task=add, schedule=30, args=[3, 4])

    # 每分钟执行一次，高优先级
    scheduler.schedule_periodic_task(
        task_name="process-every-minute",
        task=process_data,
        schedule=60,
        kwargs={"data_id": "PERIODIC_DATA"},
        queue="high_priority",
        priority=7,
    )

    # 使用crontab表达式: 每天上午10:30执行
    cron = scheduler.create_crontab(minute=30, hour=10)
    scheduler.schedule_periodic_task(
        task_name="daily-job", task=process_data, schedule=cron, kwargs={"data_id": "DAILY_DATA"}, queue="low_priority"
    )

    # 使用crontab表达式: 每周一至周五的工作时间(9:00-18:00)每小时执行一次
    workday_cron = scheduler.create_crontab(minute=0, hour="9-18", day_of_week="mon-fri")
    scheduler.schedule_periodic_task(
        task_name="workday-hourly-job",
        task=process_data,
        schedule=workday_cron,
        kwargs={"data_id": "WORKDAY_HOURLY_DATA"},
    )

    logger.info("周期性任务已设置")


def example_cancel_task():
    """演示取消任务"""
    # 调度一个延迟执行的任务
    result = scheduler.schedule_task(process_data, kwargs={"data_id": "TO_BE_CANCELED"}, countdown=30)
    logger.info(f"已调度任务: {result.id}, 即将取消")

    # 取消任务
    time.sleep(2)
    success = scheduler.cancel_task(result.id)
    logger.info(f"取消任务结果: {'成功' if success else '失败'}")


if __name__ == "__main__":
    # 运行示例
    example_one_time_task()

    # 设置周期性任务
    example_periodic_tasks()

    # 演示取消任务
    example_cancel_task()

    # 注意: 要运行worker和beat，需要在命令行执行:
    # 启动worker: python -m celery -A celery_example.scheduler.app worker --loglevel=INFO
    # 启动worker指定队列: python -m celery -A celery_example.scheduler.app worker -Q high_priority,default --loglevel=INFO
    # 启动beat: python -m celery -A celery_example.scheduler.app beat --loglevel=INFO

    # 或者通过代码启动(仅用于开发/测试环境):
    # scheduler.start_worker(queues=['default', 'high_priority', 'low_priority'])  # 启动worker
    # scheduler.start_beat()    # 启动beat
