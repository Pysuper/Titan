# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：log_test.py
@Author  ：PySuper
@Date    ：2025-04-27 19:56
@Desc    ：Titan log_test
"""
from logic import get_logger

# 获取普通日志记录器
logic = get_logger("logic")

# 获取JSON格式的日志记录器
json_logger = get_logger("json")

if __name__ == "__main__":
    # 测试普通日志
    logic.debug("测试日志")
    logic.info("测试日志")
    logic.warning("测试日志")
    logic.error("测试日志")
    logic.critical("测试日志")

    # 测试JSON格式日志
    json_logger.debug("JSON测试日志")
    json_logger.info("JSON测试日志", extra={"user_id": 12345, "action": "login"})
    json_logger.warning("JSON测试日志", extra={"status": "warning", "code": 403})
    json_logger.error("JSON测试日志", extra={"error_code": "AUTH_FAILED"})
    json_logger.critical("JSON测试日志", extra={"critical_error": True, "needs_attention": True})

    # 测试结构化数据
    data = {
        "user": {"id": 1001, "name": "测试用户", "roles": ["admin", "user"]},
        "action": "data_export",
        "timestamp": "2025-04-27T20:00:00",
    }
    json_logger.info(f"处理用户数据", extra={"data": data})

    # 测试异常记录
    try:
        result = 10 / 0
    except Exception as e:
        json_logger.exception(f"发生异常: {str(e)}")

    from decorators.logs import json_log

    @json_log
    def process_data(data, threshold=0.5):
        """处理数据的示例函数"""
        # 处理逻辑
        result = [x for x in data if x > threshold]
        return result

    # 调用函数
    process_data([0.1, 0.6, 0.8, 0.4, 0.9], threshold=0.7)
