"""
@Project ：Titan
@File    ：main_mid.py
@Author  ：PySuper
@Date    ：2025/4/29 14:00
@Desc    ：Titan main_mid.py
"""

from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logic.config import logger
from middleware import *

app = FastAPI()

# 使用工厂函数创建中间件
# def create_request_parser_middleware() -> Callable[[FastAPI], BaseHTTPMiddleware]:
#     def middleware_factory(app: FastAPI) -> BaseHTTPMiddleware:
#         return RequestParserMiddleware(app)
#
#     return middleware_factory


# 添加所有中间件到应用
def add_all_middlewares(app: FastAPI, config: Dict[str, Any] = None) -> None:
    """
    添加所有中间件到FastAPI应用

    Args:
        app: FastAPI应用实例
        config: 中间件配置字典
    """
    config = config or {}

    # 添加超时中间件 TODO： 超时中间件应该放在最前面
    app.add_middleware(TimeoutMiddleware, timeout=config.get("timeout", 30.0))

    # 添加跨域中间件
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )

    # 添加请求参数解析中间件
    app.add_middleware(RequestParserMiddleware)

    # 添加异常处理中间件
    app.add_middleware(ExceptionHandlerMiddleware)

    # 添加日志中间件
    app.add_middleware(LoggingMiddleware)

    # 添加性能监控中间件
    app.add_middleware(PerformanceMonitorMiddleware)

    # 添加安全中间件
    app.add_middleware(SecurityMiddleware, allowed_ips=config.get("allowed_ips"))

    # 添加限流中间件
    app.add_middleware(
        RateLimitMiddleware,
        # global_rate_limit=None,  # 全局限流
        # ip_rate_limit=None,  # IP 限流
        # path_rate_limits=None,  # 路径限流
        # window_size=None,  # 窗口大小
        # block_duration=None,  # 阻塞时长
    )

    # # 添加鉴权中间件 TODO: 可用，需要配置Token
    # app.add_middleware(
    #     AuthenticationMiddleware, api_keys=config.get("api_keys"), exclude_paths=config.get("auth_exclude_paths")
    # )

    # 添加缓存中间件 TODO: 当前连POST请求一起缓存了，使用时在关闭
    app.add_middleware(
        CacheMiddleware, redis_url=config.get("redis_url", "redis://localhost:6379/0"), ttl=config.get("cache_ttl", 300)
    )

    # # 添加负载均衡中间件 TODO：有BUG
    # app.add_middleware(
    #     LoadBalancerMiddleware, backends=config.get("backends"), strategy=config.get("lb_strategy", "round_robin")
    # )
    #
    # # 添加流量控制中间件
    # app.add_middleware(TrafficControlMiddleware, max_body_size=config.get("max_body_size", 10 * 1024 * 1024))
    #
    # # 添加流量监控中间件
    # app.add_middleware(TrafficMonitorMiddleware)
    #
    # # 添加流量调度中间件
    # app.add_middleware(TrafficSchedulerMiddleware, priority_paths=config.get("priority_paths"))
    #
    # # 添加流量转发中间件 TODO：有BUG
    # app.add_middleware(TrafficForwardingMiddleware, forward_rules=config.get("forward_rules"))
    #
    # # 添加流量压缩中间件
    # app.add_middleware(
    #     CompressionMiddleware,
    #     min_size=config.get("min_compression_size", 1024),
    #     compression_level=config.get("compression_level", 6),
    # )
    #
    # # 添加流量解压缩中间件
    # app.add_middleware(DecompressionMiddleware)
    #
    # # 添加流量加密中间件
    # app.add_middleware(EncryptionMiddleware, secret_key=config.get("encryption_key"))
    #
    # # 添加流量解密中间件
    # app.add_middleware(DecryptionMiddleware, secret_key=config.get("encryption_key"))
    #
    # # 添加流量重定向中间件
    # app.add_middleware(RedirectionMiddleware, redirect_rules=config.get("redirect_rules"))
    #
    # # 添加流量路由中间件
    # app.add_middleware(RoutingMiddleware, routes=config.get("routing_config"))
    #
    # # 添加响应结果序列化中间件（最后添加，确保它是第一个执行的中间件）
    # app.add_middleware(ResponseSerializerMiddleware)

    logger.debug("所有中间件已添加到应用")


# 使用示例
# if __name__ == "__main__":
#     # 添加所有中间件
#     add_all_middlewares(
#         app,
#         {
#             "allowed_ips": ["127.0.0.1"],
#             "rate_limit": 100,
#             "timeout": 30.0,
#             "api_keys": ["test-key-1", "test-key-2"],
#             "redis_url": "redis://localhost:6379/0",
#             "backends": ["http://localhost:8001", "http://localhost:8002"],
#             "priority_paths": {"/api/high": 10, "/api/low": 3},
#             "forward_rules": {"/legacy": "http://legacy-api.example.com"},
#             "redirect_rules": {"/old": "/new"},
#         },
#     )
#
#     @app.get("/")
#     async def root():
#         return {"message": "Hello World"}
#
#     # 启动服务器
#     import uvicorn
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)
