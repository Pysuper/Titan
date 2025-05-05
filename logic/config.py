"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 21:05
@Desc    ：日志配置类
"""

import os
import sys
from typing import Dict

from loguru import logger

from logic.setting import LOG_DIR, LOG_FORMAT, LOG_LEVEL, MODULE_CONFIGS
from logic.utils import pretty_json_serializer, process_record


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

        # # 添加控制台处理器（只添加一次，避免重复输出）
        # if not cls._console_handler_added:
        #     # 根据格式类型选择控制台输出格式
        #     console_format = (
        #         log_format if format_type not in ["json", "pretty_json"] else LOG_FORMAT[LOG_LEVEL]["format"]
        #     )
        #
        #     # 准备处理器参数
        #     handler_params = {
        #         "sink": sys.stderr,  # 输出到控制台
        #         "format": console_format,  # 日志格式
        #         "colorize": LOG_FORMAT[format_type]["colorize"],  # 彩色日志
        #         "level": LOG_LEVEL.upper(),  # 日志等级
        #         "backtrace": False,  # 不显示回溯信息
        #         "diagnose": False,  # 不显示诊断信息
        #         "catch": True,  # 捕获获所有异常
        #         "enqueue": True,  # 异步日志
        #         "filter": process_record,  # 添加默认request_id
        #     }
        #
        #     # 如果是JSON格式，添加序列化参数
        #     if format_type == "json":
        #         handler_params["serialize"] = True
        #     elif format_type == "pretty_json":
        #         handler_params["serialize"] = True
        #         handler_params["format"] = "{message}"
        #         handler_params["serialize_format"] = pretty_json_serializer
        #
        #     module_logger.add(**handler_params)
        #     cls._console_handler_added = True
        #
        # # 添加文件处理器，使用日期作为文件名的一部分，按日期轮换
        # file_extension = "json" if format_type in ["json", "pretty_json"] else "log"
        #
        # # 准备文件处理器参数
        # file_handler_params = {
        #     "sink": module_log_dir / f"{module}_{{time:YYYY-MM-DD}}.{file_extension}",
        #     "rotation": config["rotation"],  # 轮换设置
        #     "retention": config["retention"],  # 保留天数
        #     "format": log_format,
        #     "level": config["level"],
        #     "compression": "zip",  # 压缩
        #     "enqueue": True,  # 异步写入
        #     "filter": lambda record: record["extra"].get("module") == module,  # 只记录该模块的日志
        # }
        #
        # # 如果是JSON格式，添加序列化参数
        # if format_type == "json":
        #     file_handler_params["serialize"] = True
        # elif format_type == "pretty_json":
        #     file_handler_params["serialize"] = True
        #     file_handler_params["format"] = "{message}"
        #
        # file_handler = module_logger.add(**file_handler_params)
        #
        # # 保存logger实例
        # cls._loggers[module] = module_logger
        # return module_logger

        if not cls._console_handler_added:
            # 添加控制台处理器（只添加一次，避免重复输出）
            cls._add_console_handler(module_logger, format_type, log_format)
            cls._console_handler_added = True

        # 添加文件处理器
        cls._add_file_handler(module_logger, module, config, format_type, log_format)

        # 保存logger实例
        cls._loggers[module] = module_logger
        return module_logger

    @classmethod
    def _add_console_handler(cls, module_logger, format_type, log_format):
        """添加控制台处理器"""
        # 根据格式类型选择控制台输出格式
        console_format = log_format if format_type not in ["json", "pretty_json"] else LOG_FORMAT[LOG_LEVEL]["format"]

        # 准备处理器参数
        handler_params = {
            "sink": sys.stderr,  # 输出到控制台
            "format": console_format,  # 日志格式
            "colorize": LOG_FORMAT[format_type]["colorize"],  # 彩色日志
            "level": LOG_LEVEL.upper(),  # 日志等级
            "backtrace": False,  # 不显示回溯信息
            "diagnose": False,  # 不显示诊断信息
            "catch": True,  # 捕获所有异常
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

    @classmethod
    def _add_file_handler(cls, module_logger, module, config, format_type, log_format):
        """添加文件处理器"""
        # 添加文件处理器，使用日期作为文件名的一部分，按日期轮换
        file_extension = "json" if format_type in ["json", "pretty_json"] else "log"

        # 准备文件处理器参数
        file_handler_params = {
            "sink": LOG_DIR / module / f"{module}_{{time:YYYY-MM-DD}}.{file_extension}",
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

        module_logger.add(**file_handler_params)

        # 如果是error模块，添加错误日志处理器
        if module == "error":
            cls._add_error_handler(module_logger, module, format_type, log_format)

    @classmethod
    def _add_error_handler(cls, module_logger, module, format_type, log_format):
        """添加错误日志处理器"""
        file_extension = "json" if format_type in ["json", "pretty_json"] else "log"

        # 准备错误日志处理器参数
        error_handler_params = {
            "sink": LOG_DIR / module / f"all_errors_{{time:YYYY-MM-DD}}.{file_extension}",
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
        module_logger.add(**error_handler_params)

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
