"""
@Project ：Titan
@File    ：algorithm.py
@Author  ：PySuper
@Date    ：2025/4/29 11:54
@Desc    ：Titan algorithm.py
"""

SERVER_IP = "localhost"
TASK_PORT = 9003
RESULT_PORT = 8000

# 任务推送 URL
TASK_PUSH_URL = f"http://{SERVER_IP}:{TASK_PORT}/api/task"
RESULT_SEND_URL = f"http://{SERVER_IP}:{RESULT_PORT}/api/result"


HEARTBEAT_INTERVAL = 10  # 心跳间隔（秒）
HEARTBEAT_URL = f"http://{SERVER_IP}:{RESULT_PORT}/api/heartbeat"
