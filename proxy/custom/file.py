"""
@Project ：Titan
@File    ：file.py
@Author  ：PySuper
@Date    ：2025/4/28 11:39
@Desc    ：Titan file.py
"""

import os

import tornado.web
import tornado.websocket

from config.files import UPLOAD_DIR
from logic.config import get_logger

logger = get_logger("proxy")


class FileStream(tornado.iostream.IOStream):
    """
    自定义的文件流类，用于处理文件的读取和写入操作
    """

    def get(self, file_path):
        """
        根据请求URL，找到视频文件，返回数据
        如：http://localhost:9000/files/person.mp4

        :param file_path: 通过路由捕获的文件路径部分
        """
        if not file_path:
            self.set_status(400)
            self.write("File path is required")
            return

        file_path = os.path.join(UPLOAD_DIR, file_path)
        if not os.path.exists(file_path):
            self.set_status(404)
            self.write("File not found")
            return

        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")

        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                self.write(chunk)
        self.finish()

    def __init__(self, file_path, chunk_size=1024 * 1024):
        """
        初始化文件流
        @param file_path: 文件路径
        @param chunk_size: 每次读取的块大小
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.file = None
        self.total_size = 0
        self.read_offset = 0

    def open(self):
        """
        打开文件
        :return: 是否成功打开文件
        """
        try:
            self.file = open(self.file_path, "rb")
            self.total_size = os.path.getsize(self.file_path)  # 获取文件大小
            return True
        except IOError as e:
            logger.error(f"打开文件时出错: {str(e)}")
            return False

    def close(self):
        """
        关闭文件
        :return: 是否成功关闭文件
        """
        try:
            if self.file:
                self.file.close()
                return True
        except IOError as e:
            logger.error(f"关闭文件时出错: {str(e)}")
            return False
        return False

    def read(self):
        """
        读取文件内容
        :return: 文件内容
        """
        if not self.file:
            return None
        self.file.seek(self.read_offset)
        data = self.file.read(self.chunk_size)
        self.read_offset += len(data)
        return data

    def is_eof(self):
        """
        判断是否到达文件末尾
        :return: 是否到达文件末尾
        """
        return self.read_offset >= self.total_size


class VideoStreamHandler(tornado.web.RequestHandler):
    """
    视频流处理类，用于处理视频文件的流式传输
    """

    async def get(self):
        """
        处理GET请求，用于流式传输视频文件
        """
        video_path = self.get_argument("path", None)
        if not video_path:
            self.set_status(400)
            self.write("缺少参数: path")
            return

        # 打开视频文件
        video_stream = FileStream(video_path)
        if not video_stream.open():
            self.set_status(404)
            self.write("找不到视频文件")
            return

        # 设置响应头
        self.set_header("Content-Type", "video/mp4")
        self.set_header("Content-Disposition", f"attachment; filename={os.path.basename(video_path)}")  # 文件名
        # 开始流式传输
        while not video_stream.is_eof():
            data = video_stream.read()
            if not data:
                break
            await self.write(data)
            await self.flush()

        # 关闭文件
        video_stream.close()
