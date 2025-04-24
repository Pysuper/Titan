"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 21:05
@Desc    ：日志配置类
"""

import sys

from loguru import logger


class LogConfig:
    """
    loguru日志配置类
    """

    @staticmethod
    def setup_logger():
        """
        配置和设置logger
        """
        # 清除默认的处理器
        logger.remove()

        # 配置日志格式
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        # 添加控制台处理器
        logger.add(sys.stderr, format=log_format, level="INFO", enqueue=True)

        # 添加文件处理器
        logger.add(
            "logs/app_{time}.log",
            rotation="500 MB",
            retention="10 days",
            format=log_format,
            level="DEBUG",
            compression="zip",
            enqueue=True,
        )

        return logger


# 实例化logger
logic = LogConfig.setup_logger()
