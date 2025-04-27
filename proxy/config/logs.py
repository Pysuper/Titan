"""
@Project ：Titan
@File    ：logs.py
@Author  ：PySuper
@Date    ：2025/4/25 15:36
@Desc    ：每个模块的日志配置
"""

import os
from pathlib import Path

from loguru import logger
import sys

# TODO: 期望统一管理日志，怎么实现？
# ------------------------------------------------------------
LOG_LEVEL = "debug"
PROXY_ROOT = Path(__file__).resolve(strict=True).parent.parent / "logs"
if not os.path.exists(PROXY_ROOT):
    os.makedirs(PROXY_ROOT)

client_log_dir = os.path.join(PROXY_ROOT, "client/wc_client_{time}.log")

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(client_log_dir, level="DEBUG", rotation="10 MB", compression="zip")
