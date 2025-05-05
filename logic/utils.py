# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：utils.py
@Author  ：PySuper
@Date    ：2025-05-05 13:20
@Desc    ：Titan utils
"""
import datetime
import json
import pprint


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
        # 使用字典解包简化额外信息的添加
        **{k: v for k, v in record["extra"].items() if k != "module"},  # 添加所有额外信息
    }

    # # 添加额外信息
    # for key, value in record["extra"].items():
    #     if key != "module":  # 避免重复
    #         log_data[key] = value

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


# 添加默认请求ID处理器
def process_record(record):
    """为日志记录添加默认的request_id"""
    # if "request_id" not in record["extra"]:
    #     record["extra"]["request_id"] = "TiTan"

    # 使用 setdefault 简化默认值设置
    record["extra"].setdefault("request_id", "TiTan")
    return record
