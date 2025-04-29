"""
@Project ：Titan
@File    ：main.py
@Author  ：PySuper
@Date    ：2025/4/25 13:51
@Desc    ：Titan main.py
"""

import os
import signal

import tornado
import tornado.httpserver
import tornado.ioloop
import tornado.netutil
from tornado.web import StaticFileHandler

from logic.config import get_logger
from proxy.server import HttpProxy, WsProxy
from utils.system import close_port

# 创建一个系统级别的logger
logger = get_logger("proxy-server")


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
    # 生成启动标识ID
    # startup_id = str(uuid.uuid4())[:8]
    # log = logger.bind(request_id=f"startup_{startup_id}")

    # 定义静态文件目录
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    upload_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    # 确保目录存在
    for path in [static_path, template_path, upload_path]:
        if not os.path.exists(path):
            os.makedirs(path)
            logger.debug(f"创建目录: {path}")

    # 定义路由规则
    handlers = [
        # API 路由
        # (r"/api/upload", FaceProxy),  # 文件上传接口
        (r"/api/websocket", WsProxy),  # WebSocket连接
        (r"/api/control", HttpProxy),  # 控制接口
        # (r"/api/video_control", FaceProxy),  # 视频控制接口
        # 静态文件路由
        # (r"/files/(.*)", FileProxy),  # 文件访问接口
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
    logger.debug(f"Tornado调试模式: {settings['debug']}")
    logger.debug(f"静态文件目录: {static_path}")
    logger.debug(f"上传文件目录: {upload_path}")
    logger.debug(f"注册的路由数量: {len(handlers)}")

    return app


def handle_signal(sig, frame):
    """处理系统信号，优雅关闭服务器"""
    # log = logger.bind(request_id="shutdown")
    logger.info(f"接收到信号 {sig}，服务器正在优雅关闭...")

    # 获取当前的IOLoop实例
    ioloop = tornado.ioloop.IOLoop.current()

    # 使用ioloop.add_callback来安全地停止
    ioloop.add_callback_from_signal(ioloop.stop)


def main():
    """主程序入口"""
    # 创建一个带有请求ID的日志记录器
    # log = logger.bind(request_id="server_startup")

    # 检查端口占用情况并释放端口
    logger.debug("检查端口占用情况...")
    close_port(9000, logger)
    close_port(9001, logger)

    try:
        # 创建应用
        logger.debug("正在初始化Titan服务器...")
        app = make_app()

        # 设置HTTP服务器
        logger.debug("正在启动HTTP服务器...")
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.listen(9000, address="0.0.0.0")
        logger.debug("HTTP      服务器：已启动，监听端口: 9000")

        # 设置WebSocket服务器
        logger.debug("正在启动WebSocket服务器...")
        ws_server = tornado.httpserver.HTTPServer(app)
        ws_server.add_sockets(tornado.netutil.bind_sockets(9001))
        logger.debug("WebSocket 服务器：已启动，监听端口: 9001")

        # 注册信号处理器
        signal.signal(signal.SIGINT, handle_signal)  # 处理Ctrl+C
        signal.signal(signal.SIGTERM, handle_signal)  # 处理终止信号

        # 启动服务
        logger.info("✅ Titan服务器启动完成，正在运行...")
        logger.debug("按Ctrl+C停止服务器")

        # 启动事件循环
        tornado.ioloop.IOLoop.current().start()

        # 如果到达这里，说明事件循环已停止
        logger.info("Titan服务器已关闭")

    except Exception as e:
        logger.error(f"服务器启动过程中出现错误: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    # print("🔌 WebSocket 已连接")  # 插头符号
    # print("📡 WebSocket 通信中")  # 天线符号
    # print("❌ WebSocket 已断开")  # 叉号符号
    exit_code = main()
    exit(exit_code)
