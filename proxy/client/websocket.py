"""
@Project ：Titan
@File    ：websocket.py
@Author  ：PySuper
@Date    ：2025/4/25 13:52
@Desc    ：WebSocket Client
"""

import argparse
import asyncio
import json
import signal

import websockets

from proxy.config.logs import logger


class WebSocketClient:
    """
    WebSocket客户端
    """

    def __init__(self, uri):
        self.uri = uri
        self.connected = False
        self.websocket = None
        self.should_exit = False

    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info(f"已连接: {self.uri}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            return False

    async def disconnect(self):
        """断开WebSocket连接"""
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("已断开")

    async def receive_messages(self):
        """接收并处理WebSocket消息"""
        if not self.connected:
            logger.error("未找到服务")
            return

        try:
            while not self.should_exit:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    try:
                        data = json.loads(message)
                        logger.info(f"接收到数据: {json.dumps(data, ensure_ascii=False)[:100]}...")
                        if data.get("status") == "ready":
                            await self.websocket.send(json.dumps({"action": "play_video"}))
                    except json.JSONDecodeError:
                        logger.warning(f"非JSON格式消息: {message}")
                except asyncio.TimeoutError:
                    # 超时，继续循环并检查should_exit标志
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.warning("已关闭")
        except Exception as e:
            logger.error(f"接收消息时出错: {str(e)}")

    def handle_exit(self):
        """处理退出信号"""
        self.should_exit = True
        logger.info("正在退出...")

    async def run(self):
        """运行WebSocket客户端"""
        if not await self.connect():
            return

        try:
            await self.receive_messages()
        except KeyboardInterrupt:
            logger.info("手动中断")
            self.handle_exit()
        finally:
            await self.disconnect()


async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="WebSocket客户端，用于接收算法结果")
    parser.add_argument(
        "--uri",
        type=str,
        default="ws://localhost:9001/websocket",
        help="WebSocket服务器地址 (默认: ws://localhost:9001/websocket)",
    )
    args = parser.parse_args()

    # 创建WebSocket客户端
    client = WebSocketClient(args.uri)

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: client.handle_exit())
    except NotImplementedError:
        # Windows系统使用信号模块直接设置处理程序（不支持add_signal_handler）
        signal.signal(signal.SIGINT, lambda s, f: client.handle_exit())
        signal.signal(signal.SIGTERM, lambda s, f: client.handle_exit())

    logger.info(f"尝试连接: {args.uri}")

    # 运行客户端
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
