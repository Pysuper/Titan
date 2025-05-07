"""
@Project ：Titan
@File    ：algorithm.py
@Author  ：PySuper
@Date    ：2025/4/29 11:54
@Desc    ：Titan algorithm.py
"""

# 服务器 IP 地址
SERVER_IP = "localhost"
TASK_PORT = 9003
RESULT_PORT = 8000

# 任务推送 URL
TASK_PUSH_URL = f"http://{SERVER_IP}:{TASK_PORT}/api/task"
RESULT_SEND_URL = f"http://{SERVER_IP}:{TASK_PORT}/api/result"

# 心跳检查 URL
HEARTBEAT_INTERVAL = 10  # 心跳间隔（秒）
HEARTBEAT_URL = f"http://{SERVER_IP}:{RESULT_PORT}/api/heartbeat"
