# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：setting.py
@Author  ：PySuper
@Date    ：2025-05-05 13:19
@Desc    ：Titan settings
"""

import os
from pathlib import Path

from logic.utils import pretty_json_serializer

# 统一日志等级
DEBUG = True
LOG_LEVEL = "debug" if DEBUG else "info"

# 定义日志路径
LOG_DIR = Path(__file__).resolve(strict=True).parent.parent / "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


# 自定义日志格式
LOG_FORMAT = {
    # 基础格式定义
    "base": {
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "  # 添加请求ID
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        "colorize": True,  # 彩色日志
        "extra": {"function": lambda record: record["function"].split(".")[-1]},  # 记录函数名
        "backtrace": False,  # 不显示回溯信息
        "diagnose": False,  # 不显示诊断信息
        "catch": (Exception,),  # 捕获所有异常
    },
}

# 使用字典推导式生成不同级别的日志格式
for level in ["info", "debug", "warning", "error", "critical"]:
    LOG_FORMAT[level] = {
        **LOG_FORMAT["base"],
        "level": level.upper(),
    }

# 添加JSON格式
LOG_FORMAT["json"] = {
    "format": "{message}",  # 使用简单的消息格式，实际内容将由serialize处理
    "colorize": False,  # JSON不需要颜色
    "level": LOG_LEVEL.upper(),
    "backtrace": False,
    "diagnose": False,
    "catch": (Exception,),
    "serialize": True,  # 启用序列化
}

# 添加美化JSON格式
LOG_FORMAT["pretty_json"] = {
    "format": "{message}",  # 使用简单的消息格式，实际内容将由serialize处理
    "colorize": True,  # 美化输出需要颜色
    "level": LOG_LEVEL.upper(),
    "backtrace": False,
    "diagnose": False,
    "catch": (Exception,),
    "serialize": pretty_json_serializer,  # 使用自定义序列化函数
}


# 定义基础模块配置
BASE_MODULE_CONFIG = {
    "rotation": "00:00",  # 每天午夜轮换
    "retention": "30 days",
    "level": LOG_LEVEL.upper(),
}

# 定义模块配置
MODULE_CONFIGS = {
    "default": {
        "file_name": "titan",
        **BASE_MODULE_CONFIG,
    },
    "algorithm": {
        "file_name": "algorithm",
        **BASE_MODULE_CONFIG,
    },
    "proxy": {
        "file_name": "proxy",
        "retention": "15 days",  # 覆盖基础配置
        **BASE_MODULE_CONFIG,
    },
    "middleware": {
        "file_name": "middleware",
        "retention": "15 days",
        **BASE_MODULE_CONFIG,
    },
    "request": {
        "file_name": "request",
        "retention": "7 days",
        **BASE_MODULE_CONFIG,
    },
    "performance": {
        "file_name": "performance",
        "retention": "90 days",
        "level": "INFO",  # 性能日志通常只需要INFO级别
        **BASE_MODULE_CONFIG,
    },
    "error": {
        "file_name": "error",
        "retention": "90 days",
        "level": "ERROR",  # 只记录错误及以上级别
        **BASE_MODULE_CONFIG,
    },
}

# 添加JSON日志配置
for json_type in ["json", "pretty_json"]:
    MODULE_CONFIGS[json_type] = {
        "file_name": f"{json_type}_logs",
        "format": json_type,  # 使用对应的JSON格式
        **BASE_MODULE_CONFIG,
    }
