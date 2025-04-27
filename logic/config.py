"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 21:05
@Desc    ：日志配置类
"""

import os
import sys
from pathlib import Path

from loguru import logger

# 统一日志等级
DEBUG = True
LOG_LEVEL = "debug" if DEBUG else "info"

# 定义日志路径
LOG_DIR = Path(__file__).resolve(strict=True).parent.parent / "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 自定义日志格式
LOG_FORMAT = {
    # 定义几个不同等级的日志格式
    "info": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "level": "INFO",
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获获所有异常
    },
    "debug": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "level": "DEBUG",
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获获所有异常
    },
    "warning": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "level": "WARNING",
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获获所有异常
    },
    "error": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "level": "ERROR",
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获获所有异常
    },
    "critical": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "level": "CRITICAL",
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获获所有异常
    },
}


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
        log_format = LOG_FORMAT[LOG_LEVEL]["format"]
        # log_format = (
        #     "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        #     "<level>{level: <8}</level> | "
        #     "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        #     "<level>{message}</level>"
        # )

        # 添加控制台处理器
        logger.add(
            sys.stderr,  # 输出到控制台
            format=LOG_FORMAT[LOG_LEVEL]["format"],  # 日志格式
            colorize=True,  # 彩色日志
            level=LOG_LEVEL.upper(),  # 日志等级
            backtrace=False,  # 不显示回溯信息
            diagnose=False,  # 不显示诊断信息
            catch=True,  # 捕获获所有异常
            enqueue=True,  # 异步日志
        )

        # 添加文件处理器
        logger.add(
            LOG_DIR / "TaiTan_{time}.log",
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
