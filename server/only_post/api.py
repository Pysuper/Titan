"""
@Project ：Titan
@File    ：api.py
@Author  ：PySuper
@Date    ：2025/4/29 10:53
@Desc    ：API路由定义
"""

from fastapi import HTTPException

from algorithm.main import Parse
from .models import PostData, ResultData


# POST请求处理路由
def task(data: PostData):
    try:
        parse_math = Parse()  # 实例化Parse类
        parse_math.execute_algorithm("math-b", data.data)

        # TODO: 在这里调用 任务调度器 进行任务分发

        return {"status": "success", "message": "任务已成功接收"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})


# 结果处理路由
def result(result: ResultData):
    try:
        # 处理接收到的数据
        response = {
            "status": "success",
            "message": f"成功接收到结果: {result.message}",
            "data": result.data,
        }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": str(e), "data": None},
        )


# 健康检查路由
async def health_check():
    return {"status": "healthy", "message": "服务正常运行"}
