# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：log_test.py
@Author  ：PySuper
@Date    ：2025-04-27 19:56
@Desc    ：Titan log_test
"""
from logic.config import get_logger

logic = get_logger("logic")

if __name__ == "__main__":
    logic.debug("测试日志")
    logic.info("测试日志")
    logic.warning("测试日志")
    logic.error("测试日志")
    logic.critical("测试日志")
