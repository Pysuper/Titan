"""
@Project ：Titan
@File    ：main.py
@Author  ：PySuper
@Date    ：2025/4/29 10:53
@Desc    ：主程序入口
"""

import sys

import uvicorn
from fastapi import FastAPI

from logic.config import get_logger
from server.only_post.api import task, result, health_check
from server.only_post.mid import add_all_middlewares
from server.only_post.models import ResponseData
from server.only_post.util import global_exception_handler
from utils.system import close_port

logger = get_logger("FastAPI")

# 创建FastAPI应用
app = FastAPI(title="Titan POST API", description="只接受POST请求的API服务")

# 注册异常处理器
app.add_exception_handler(Exception, global_exception_handler)

# 注册中间件
add_all_middlewares(
    app,
    {
        "allowed_ips": ["127.0.0.1"],
        # "allowed_ips": ["pyro.affectai.cn", "mood.affectai.cn"],
        "rate_limit": 100,
        "timeout": 3.0,
        "api_keys": ["test-key-1", "test-key-2"],
        "redis_url": "redis://:Affect_PySuper@1.92.200.169:3218/13",
        "backends": ["http://localhost:8001", "http://localhost:8002"],
        "priority_paths": {"/api/high": 10, "/api/low": 3},
        "forward_rules": {"/legacy": "http://legacy-api.example.com"},
        "redirect_rules": {"/old": "/new"},
    },
)

# 注册路由
app.post("/api/task", response_model=ResponseData)(task)
app.post("/api/result", response_model=ResponseData)(result)
app.post("/health")(health_check)


def start_server(host="localhost", port=9003):
    """启动服务器的函数，可以在其他地方调用"""
    # 先尝试关闭可能占用的端口
    close_port(port, logger)
    print(f"Starting server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # 从命令行获取端口参数（如果有）
    port = 9003
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}, using default: 9003")

    # 使用PyCharm时，要在配置中修改端口号，或者
    start_server(port=port)
