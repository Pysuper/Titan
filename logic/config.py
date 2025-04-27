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
from typing import Dict

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

# 定义模块配置
MODULE_CONFIGS = {
    "default": {
        "file_name": "titan",
        "rotation": "500 MB",  # 使用大小轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
    },
    "algorithm": {
        "file_name": "algorithm",
        "rotation": "500 MB",  # 使用大小轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
    },
    "proxy": {
        "file_name": "proxy",
        "rotation": "200 MB",  # 使用大小轮换
        "retention": "15 days",
        "level": LOG_LEVEL.upper(),
    },
    "middleware": {
        "file_name": "middleware",
        "rotation": "200 MB",  # 使用大小轮换
        "retention": "15 days",
        "level": LOG_LEVEL.upper(),
    },
    "request": {
        "file_name": "request",
        "rotation": "100 MB",  # 使用大小轮换
        "retention": "7 days",
        "level": LOG_LEVEL.upper(),
    },
    "performance": {
        "file_name": "performance",
        "rotation": "1 GB",  # 使用大小轮换
        "retention": "90 days",
        "level": "INFO",  # 性能日志通常只需要INFO级别
    },
    "error": {
        "file_name": "error",
        "rotation": "500 MB",  # 使用大小轮换
        "retention": "90 days",
        "level": "ERROR",  # 只记录错误及以上级别
    },
}


class LogConfig:
    """
    loguru日志配置类
    """

    _initialized: bool = False
    _loggers: Dict[str, logger] = {}
    _console_handler_added: bool = False

    @classmethod
    def setup_logger(cls, module: str = "default") -> logger:
        """
        配置和设置logger

        :param module: 模块名称，用于选择配置和文件名
        :return: 配置好的logger实例
        """
        # 如果已经初始化过该模块的logger，直接返回
        if module in cls._loggers:
            return cls._loggers[module]

        # 获取模块配置，如果不存在则使用默认配置
        config = MODULE_CONFIGS.get(module, MODULE_CONFIGS["default"])

        # 创建该模块的日志目录
        module_log_dir = LOG_DIR / module
        if not os.path.exists(module_log_dir):
            os.makedirs(module_log_dir)

        # 创建新的logger实例
        module_logger = logger.bind(module=module)

        # 清除默认的处理器
        if not cls._initialized:
            logger.remove()
            cls._initialized = True

        # 配置日志格式
        log_format = LOG_FORMAT[LOG_LEVEL]["format"]

        # 添加控制台处理器（只添加一次，避免重复输出）
        if not cls._console_handler_added:
            module_logger.add(
                sys.stderr,  # 输出到控制台
                format=LOG_FORMAT[LOG_LEVEL]["format"],  # 日志格式
                colorize=True,  # 彩色日志
                level=LOG_LEVEL.upper(),  # 日志等级
                backtrace=False,  # 不显示回溯信息
                diagnose=False,  # 不显示诊断信息
                catch=True,  # 捕获获所有异常
                enqueue=True,  # 异步日志
            )
            cls._console_handler_added = True

        # 添加文件处理器，使用日期作为文件名的一部分，但按大小轮换
        file_handler = module_logger.add(
            # module_log_dir / f"{config['file_name']}_{module}_{{time:YYYY-MM-DD}}.log",
            module_log_dir / f"{module}_{{time:YYYY-MM-DD}}.log",
            rotation=config["rotation"],  # 按大小轮换
            retention=config["retention"],  # 保留天数
            format=log_format,
            level=config["level"],
            compression="zip",  # 压缩
            enqueue=True,  # 异步写入
            filter=lambda record: record["extra"].get("module") == module,  # 只记录该模块的日志
        )

        # 如果是error模块，添加错误日志处理器
        if module == "error":
            # 添加错误日志处理器（记录所有模块的错误）
            error_file_handler = module_logger.add(
                module_log_dir / f"all_errors_{{time:YYYY-MM-DD}}.log",
                rotation="500 MB",  # 按大小轮换
                retention="90 days",  # 保留90天
                format=log_format,
                level="ERROR",  # 只记录错误及以上级别
                compression="zip",  # 压缩
                enqueue=True,  # 异步写入
                # 不过滤模块，记录所有错误
            )

        # 保存logger实例
        cls._loggers[module] = module_logger
        return module_logger

    @classmethod
    def get_logger(cls, module: str = "default") -> logger:
        """
        获取指定模块的logger

        :param module: 模块名称
        :return: logger实例
        """
        if module not in cls._loggers:
            return cls.setup_logger(module)
        return cls._loggers[module]


# 实例化默认logger
# logic = LogConfig.setup_logger("default")


# 不再预先创建所有模块的logger，而是在需要时通过get_logger获取
def get_logger(module: str = "default") -> logger:
    """
    获取指定模块的logger的便捷函数

    :param module: 模块名称
    :return: logger实例
    """
    return LogConfig.get_logger(module)


"""

# 在代码中使用
from logic.config import get_logger

# 获取特定模块的logger
logger = get_logger("algorithm")
logger.info("这是算法模块的日志")

# 记录错误（会同时写入模块日志和错误日志）
logger.error("发生了一个错误")

# 也可以直接导入预定义的logger
from logic.config import get_logger
algorithm_logger = get_logger("algorithm")
error_logger = get_logger("error")

algorithm_logger.debug("算法调试信息")
error_logger.error("严重错误，需要立即处理")

"""
