"""
@Project ：Titan
@File    ：main.py
@Author  ：PySuper
@Date    ：2025/4/25 13:51
@Desc    ：Titan main.py
"""

import os

import tornado
from loguru import logger
from proxy.server import HttpProxy, WsProxy, AllStream
from tornado.web import StaticFileHandler

from proxy.server.http import HttpProxy
from utils.system import close_port


def make_app():
    """
    配置tornado应用程序

    功能：
    1. 设置路由规则，将URL路径映射到对应的处理类
    2. 配置静态文件目录，用于提供前端资源
    3. 设置应用程序级别的配置项
    4. 配置安全相关选项
    5. 设置调试模式和日志级别

    :return: tornado应用程序实例
    """

    # 定义静态文件目录
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    upload_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    # 确保目录存在
    for path in [static_path, template_path, upload_path]:
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"创建目录: {path}")

    # 定义路由规则
    handlers = [
        # API 路由
        (r"/api/upload", FaceProxy),  # 文件上传接口
        (r"/api/websocket", WebSocketHandler),  # WebSocket连接
        (r"/api/control", HttpProxy),  # 控制接口
        (r"/api/video_control", FaceProxy),  # 视频控制接口
        # 静态文件路由
        (r"/files/(.*)", FileProxy),  # 文件访问接口
        (r"/static/(.*)", StaticFileHandler, {"path": static_path}),  # 静态资源
        (r"/uploads/(.*)", StaticFileHandler, {"path": upload_path}),  # 上传文件访问
        # 默认路由 - 可以重定向到首页或返回404
        (r"/(.*)", StaticFileHandler, {"path": template_path, "default_filename": "index.html"}),
    ]

    # 应用程序设置
    settings = {
        "debug": True,  # 开发模式下启用调试
        "autoreload": True,  # 代码变更时自动重载
        "compress_response": True,  # 压缩HTTP响应
        "serve_traceback": True,  # 在调试模式下显示错误堆栈
        "static_path": static_path,  # 静态文件目录
        "template_path": template_path,  # 模板文件目录
        "cookie_secret": os.environ.get("COOKIE_SECRET", "Titan_Secret_Key_2025"),  # Cookie加密密钥
        "xsrf_cookies": False,  # 暂时禁用XSRF保护，根据需要启用
        "websocket_ping_interval": 30,  # WebSocket心跳间隔(秒)
        "websocket_ping_timeout": 120,  # WebSocket心跳超时(秒)
        "ws_handler_map": {},  # WebSocket处理器映射
        "upload_path": upload_path,  # 上传文件保存目录
        "max_buffer_size": 1024 * 1024 * 100,  # 最大缓冲区大小(100MB)
        "max_body_size": 1024 * 1024 * 200,  # 最大请求体大小(200MB)
    }

    # 创建并返回应用程序实例
    app = tornado.web.Application(handlers, **settings)

    # 记录应用程序配置信息
    logger.info(f"Tornado应用程序已配置 - 调试模式: {settings['debug']}")
    logger.info(f"静态文件目录: {static_path}")
    logger.info(f"上传文件目录: {upload_path}")
    logger.info(f"注册的路由数量: {len(handlers)}")

    return app


if __name__ == "__main__":
    close_port(9000)
    close_port(9001)
    try:
        app = make_app()
        server = tornado.httpserver.HTTPServer(app)
        server.listen(9000, address="0.0.0.0")
        ws_server = tornado.httpserver.HTTPServer(app)
        ws_server.add_sockets(tornado.netutil.bind_sockets(9001))
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
