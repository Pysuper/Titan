"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 21:05
@Desc    ：日志配置类
"""

import datetime
import json
import os
import pprint
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


def json_formatter(record):
    """
    将日志记录格式化为JSON字符串
    """
    # 提取基本日志信息
    log_data = {
        # "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),  # 自动添加时间戳
        "level": record["level"].name,
        "message": record["message"],
        "module": record["extra"].get("module", record["name"]),
        "function": record["function"],
        "line": record["line"],
        "process_id": record["process"].id,
        "thread_id": record["thread"].id,
    }

    # 添加额外信息
    for key, value in record["extra"].items():
        if key != "module":  # 避免重复
            log_data[key] = value

    # 添加异常信息（如果有）
    if record["exception"]:
        log_data["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }

    # 返回格式化的JSON字符串
    return json.dumps(log_data, ensure_ascii=False)  # 确保中文字符正确显示


def pretty_json_serializer(record):
    """
    将日志记录序列化为格式化的JSON字符串，用于控制台输出
    """
    # 提取基本日志信息
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["extra"].get("module", record["name"]),
        "function": record["function"],
        "line": record["line"],
    }

    # 添加额外信息
    for key, value in record["extra"].items():
        if key != "module":  # 避免重复
            log_data[key] = value

    # 添加异常信息（如果有）
    if record["exception"]:
        log_data["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }

    # 使用pprint格式化输出
    return pprint.pformat(log_data, indent=2, width=100)


# 自定义日志格式
LOG_FORMAT = {
    # 定义几个不同等级的日志格式
    "info": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
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
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
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
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
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
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
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
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
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
    "json": {  # 添加JSON格式
        "format": "{message}",  # 使用简单的消息格式，实际内容将由serialize处理
        "colorize": False,  # JSON不需要颜色
        "level": LOG_LEVEL.upper(),
        "backtrace": False,
        "diagnose": False,
        "catch": (Exception,),
        "serialize": True,  # 启用序列化
    },
    "pretty_json": {  # 添加美化JSON格式
        "format": "{message}",  # 使用简单的消息格式，实际内容将由serialize处理
        "colorize": True,  # 美化输出需要颜色
        "level": LOG_LEVEL.upper(),
        "backtrace": False,
        "diagnose": False,
        "catch": (Exception,),
        "serialize": pretty_json_serializer,  # 使用自定义序列化函数
    },
}

# 定义模块配置
MODULE_CONFIGS = {
    "default": {
        "file_name": "titan",
        # "rotation": "500 MB",  # 使用大小轮换
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
    },
    "algorithm": {
        "file_name": "algorithm",
        # "rotation": "500 MB",  # 使用大小轮换
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
    },
    "proxy": {
        "file_name": "proxy",
        # "rotation": "200 MB",  # 使用大小轮换
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "15 days",
        "level": LOG_LEVEL.upper(),
    },
    "middleware": {
        "file_name": "middleware",
        # "rotation": "200 MB",  # 使用大小轮换
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "15 days",
        "level": LOG_LEVEL.upper(),
    },
    "request": {
        "file_name": "request",
        # "rotation": "100 MB",  # 使用大小轮换
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "7 days",
        "level": LOG_LEVEL.upper(),
    },
    "performance": {
        "file_name": "performance",
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "90 days",
        "level": "INFO",  # 性能日志通常只需要INFO级别
    },
    "error": {
        "file_name": "error",
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "90 days",
        "level": "ERROR",  # 只记录错误及以上级别
    },
    "json": {  # 添加JSON日志配置
        "file_name": "json_logs",
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
        "format": "json",  # 使用JSON格式
    },
    "pretty_json": {  # 添加美化JSON日志配置
        "file_name": "pretty_json_logs",
        "rotation": "00:00",  # 每天午夜轮换
        "retention": "30 days",
        "level": LOG_LEVEL.upper(),
        "format": "pretty_json",  # 使用美化JSON格式
    },
}


# 添加默认请求ID处理器
def process_record(record):
    """为日志记录添加默认的request_id"""
    if "request_id" not in record["extra"]:
        record["extra"]["request_id"] = "TiTan"
    return record


class LogConfig:
    """
    loguru日志配置类
    """

    _initialized: bool = False
    _loggers: Dict[str, logger] = {}
    _console_handler_added: bool = False

    @classmethod
    def setup_logger_back(cls, module: str = "default") -> logger:
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
        module_logger = logger.bind(module=module, request_id="TiTan")

        # 清除默认的处理器
        if not cls._initialized:
            logger.remove()
            cls._initialized = True

        # 配置日志格式
        format_type = config.get("format", LOG_LEVEL)
        log_format = LOG_FORMAT[format_type]["format"]

        # 添加控制台处理器（只添加一次，避免重复输出）
        if not cls._console_handler_added:
            # 根据格式类型选择控制台输出格式
            console_format = (
                log_format if format_type not in ["json", "pretty_json"] else LOG_FORMAT[LOG_LEVEL]["format"]
            )

            # 准备处理器参数
            handler_params = {
                "sink": sys.stderr,  # 输出到控制台
                "format": console_format,  # 日志格式
                "colorize": LOG_FORMAT[format_type]["colorize"],  # 彩色日志
                "level": LOG_LEVEL.upper(),  # 日志等级
                "backtrace": False,  # 不显示回溯信息
                "diagnose": False,  # 不显示诊断信息
                "catch": True,  # 捕获获所有异常
                "enqueue": True,  # 异步日志
                "filter": process_record,  # 添加默认request_id
            }

            # 如果是JSON格式，添加序列化参数
            if format_type == "json":
                handler_params["serialize"] = True
            elif format_type == "pretty_json":
                handler_params["serialize"] = True
                handler_params["format"] = "{message}"
                handler_params["serialize_format"] = pretty_json_serializer

            module_logger.add(**handler_params)
            cls._console_handler_added = True

        # 添加文件处理器，使用日期作为文件名的一部分，按日期轮换
        file_extension = "json" if format_type in ["json", "pretty_json"] else "log"

        # 准备文件处理器参数
        file_handler_params = {
            "sink": module_log_dir / f"{module}_{{time:YYYY-MM-DD}}.{file_extension}",
            "rotation": config["rotation"],  # 每天午夜轮换
            "retention": config["retention"],  # 保留天数
            "format": log_format,
            "level": config["level"],
            "compression": "zip",  # 压缩
            "enqueue": True,  # 异步写入
            "filter": lambda record: (process_record(record), record["extra"].get("module") == module)[
                1
            ],  # 只记录该模块的日志并处理request_id
        }

        # 如果是JSON格式，添加序列化参数
        if format_type == "json":
            file_handler_params["serialize"] = True
        elif format_type == "pretty_json":
            file_handler_params["serialize"] = True
            file_handler_params["format"] = "{message}"

        file_handler = module_logger.add(**file_handler_params)

        # 如果是error模块，添加错误日志处理器
        if module == "error":
            # 准备错误日志处理器参数
            error_handler_params = {
                "sink": module_log_dir / f"all_errors_{{time:YYYY-MM-DD}}.{file_extension}",
                "rotation": "500 MB",  # 按大小轮换
                "retention": "90 days",  # 保留90天
                "format": log_format,
                "level": "ERROR",  # 只记录错误及以上级别
                "compression": "zip",  # 压缩
                "enqueue": True,  # 异步写入
                "filter": process_record,  # 添加默认request_id
            }

            # 如果是JSON格式，添加序列化参数
            if format_type == "json":
                error_handler_params["serialize"] = True
            elif format_type == "pretty_json":
                error_handler_params["serialize"] = True
                error_handler_params["format"] = "{message}"

            # 添加错误日志处理器（记录所有模块的错误）
            error_file_handler = module_logger.add(**error_handler_params)

        # 保存logger实例
        cls._loggers[module] = module_logger
        return module_logger

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
        format_type = config.get("format", LOG_LEVEL)
        log_format = LOG_FORMAT[format_type]["format"]

        # 添加控制台处理器（只添加一次，避免重复输出）
        if not cls._console_handler_added:
            # 根据格式类型选择控制台输出格式
            console_format = (
                log_format if format_type not in ["json", "pretty_json"] else LOG_FORMAT[LOG_LEVEL]["format"]
            )

            # 准备处理器参数
            handler_params = {
                "sink": sys.stderr,  # 输出到控制台
                "format": console_format,  # 日志格式
                "colorize": LOG_FORMAT[format_type]["colorize"],  # 彩色日志
                "level": LOG_LEVEL.upper(),  # 日志等级
                "backtrace": False,  # 不显示回溯信息
                "diagnose": False,  # 不显示诊断信息
                "catch": True,  # 捕获获所有异常
                "enqueue": True,  # 异步日志
                "filter": process_record,  # 添加默认request_id
            }

            # 如果是JSON格式，添加序列化参数
            if format_type == "json":
                handler_params["serialize"] = True
            elif format_type == "pretty_json":
                handler_params["serialize"] = True
                handler_params["format"] = "{message}"
                handler_params["serialize_format"] = pretty_json_serializer

            module_logger.add(**handler_params)
            cls._console_handler_added = True

        # 添加文件处理器，使用日期作为文件名的一部分，按日期轮换
        file_extension = "json" if format_type in ["json", "pretty_json"] else "log"

        # 准备文件处理器参数
        file_handler_params = {
            "sink": module_log_dir / f"{module}_{{time:YYYY-MM-DD}}.{file_extension}",
            "rotation": config["rotation"],  # 轮换设置
            "retention": config["retention"],  # 保留天数
            "format": log_format,
            "level": config["level"],
            "compression": "zip",  # 压缩
            "enqueue": True,  # 异步写入
            "filter": lambda record: record["extra"].get("module") == module,  # 只记录该模块的日志
        }

        # 如果是JSON格式，添加序列化参数
        if format_type == "json":
            file_handler_params["serialize"] = True
        elif format_type == "pretty_json":
            file_handler_params["serialize"] = True
            file_handler_params["format"] = "{message}"

        file_handler = module_logger.add(**file_handler_params)

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


def get_logger(module: str = "default") -> logger:
    """
    获取指定模块的logger的快捷方式

    :param module: 模块名称
    :return: logger实例
    """
    return LogConfig.get_logger(module).bind(request_id=module)


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

# 使用JSON格式的日志
json_logger = get_logger("json")
json_logger.info("这是一条JSON格式的日志")
json_logger.error("这是一条JSON格式的错误日志", extra={"user_id": 123, "action": "login"})

# 使用美化JSON格式的日志
pretty_json_logger = get_logger("pretty_json")
pretty_json_logger.info("这是一条美化JSON格式的日志")
pretty_json_logger.error("这是一条美化JSON格式的错误日志", extra={"user_id": 123, "action": "login"})

# 在异常处理中使用JSON日志
try:
    # 一些可能抛出异常的代码
    result = 1 / 0
except Exception as e:
    json_logger.exception("计算过程中发生异常", extra={"input_data": {"value": 1}})
    pretty_json_logger.exception("计算过程中发生异常", extra={"input_data": {"value": 1}})
"""
