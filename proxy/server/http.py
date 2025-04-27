"""
@Project ：Titan
@File    ：http.py
@Author  ：PySuper
@Date    ：2025/4/25 13:53
@Desc    ：Titan http.py
"""

"""
@Project ：Titan
@File    ：http.py
@Author  ：PySuper
@Date    ：2025/4/25 13:53
@Desc    ：Titan http.py
"""

from typing import Any, Dict


from proxy.server.base import CustomHttp, logger


class HttpProxy(CustomHttp):
    """
    处理HTTP请求的类, 继承自CustomHttp
    根据不同的请求方式，接收参数，处理后发送消息给websocket客户端
    """

    def get(self):
        """
        接收到http get请求后，根据请求参数，执行不同的操作：
        1、向websocket发送请求
        """
        return self.handle_exception(self._handle_get)()

    def _handle_get(self):
        """
        处理GET请求的内部方法
        """
        # 接受HTTP请求参数，并校验参数
        action = self.get_argument("action", None)
        if not action:
            return self.http_err("缺少action参数")

        # 查询websocket客户端连接状态
        ws = self.get_ws()
        if not ws:
            return self.http_err("没有活跃的WebSocket连接")

        # 记录请求信息
        logger.info(f"接收到GET请求: action={action}")

        # 根据请求参数执行不同的操作
        if action == "do":
            return self._handle_do_action(ws)
        elif action == "todo":
            return self._handle_todo_action(ws)
        else:
            return self.http_err(f"不支持的action: {action}")

    def _handle_do_action(self, ws) -> None:
        """
        处理'do'动作

        @param ws: WebSocket连接
        :return: None
        """
        # 判断ws中的属性值
        if ws.do_status:
            # ws中do_status=True
            response = ws.do_status(action="do")
            logger.debug(f"执行'do'操作成功: {response}")
            return self.http_success(response, "操作执行成功")
        else:
            # ws中do_status=False
            logger.warning("执行'do'操作失败: 没有可播放的视频")
            return self.http_err("没有可播放的视频")

    def _handle_todo_action(self, ws) -> None:
        """
        处理'todo'动作

        @param ws: WebSocket连接
        :return: None
        """
        # 不监听ws中的属性值，直接执行操作
        response = ws.do_status(action="todo")
        logger.debug(f"执行'todo'操作成功: {response}")
        return self.http_success(response, "操作执行成功")

    def post(self):
        """
        处理POST请求
        """
        return self.handle_exception(self._handle_post)()

    def _handle_post(self):
        """
        处理POST请求的内部方法
        """
        # 验证必需参数
        required_params = ["action"]
        params = self.validate_params(required_params)
        if not params:
            return None  # validate_params已经设置了错误响应

        action = params["action"]
        logger.info(f"接收到POST请求: action={action}")

        # 查询websocket客户端连接状态
        ws = self.get_ws()
        if not ws:
            return self.http_err("没有活跃的WebSocket连接")

        # 根据action执行不同操作
        action_handlers = {
            "play": self._handle_play_action,
            "pause": self._handle_pause_action,
            "stop": self._handle_stop_action,
            "seek": self._handle_seek_action,
            "volume": self._handle_volume_action,
            "status": self._handle_status_action,
        }

        handler = action_handlers.get(action)
        if handler:
            return handler(ws, params)
        else:
            return self.http_err(f"不支持的action: {action}")

    def _handle_play_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理播放操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        # 可以添加视频路径参数验证
        video_path = params.get("video_path")
        if video_path:
            # 通知WebSocket客户端播放指定视频
            notification = {"action": "play", "video_path": video_path}
            if self.notify_ws(notification):
                return self.http_success({"status": "playing", "video_path": video_path}, "开始播放视频")
            else:
                return self.http_err("通知WebSocket客户端失败")
        else:
            # 如果没有指定视频路径，则播放当前视频
            if ws.do_status:
                response = ws.do_status(action="play")
                return self.http_success(response, "继续播放视频")
            else:
                return self.http_err("没有可播放的视频")

    def _handle_pause_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理暂停操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        if ws.do_status:
            response = ws.do_status(action="pause")
            return self.http_success(response, "视频已暂停")
        else:
            return self.http_err("没有正在播放的视频")

    def _handle_stop_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理停止操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        if ws.do_status:
            response = ws.do_status(action="stop")
            return self.http_success(response, "视频已停止")
        else:
            return self.http_err("没有正在播放的视频")

    def _handle_seek_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理跳转操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        position = params.get("position")
        if not position:
            return self.http_err("缺少position参数")

        try:
            position = float(position)
        except ValueError:
            return self.http_err("position参数必须是数字")

        if ws.do_status:
            response = ws.do_status(action="seek", position=position)
            return self.http_success(response, f"视频已跳转到 {position} 秒")
        else:
            return self.http_err("没有正在播放的视频")

    def _handle_volume_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理音量调节操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        volume = params.get("volume")
        if volume is None:
            return self.http_err("缺少volume参数")

        try:
            volume = float(volume)
            if not 0 <= volume <= 1:
                return self.http_err("volume参数必须在0到1之间")
        except ValueError:
            return self.http_err("volume参数必须是数字")

        if ws.do_status:
            response = ws.do_status(action="volume", volume=volume)
            return self.http_success(response, f"音量已设置为 {volume}")
        else:
            return self.http_err("没有正在播放的视频")

    def _handle_status_action(self, ws, params: Dict[str, Any]) -> None:
        """
        处理获取状态操作

        @param ws: WebSocket连接
        @param params: 请求参数
        :return: None
        """
        response = ws.do_status(action="status")
        return self.http_success(response, "获取状态成功")

    def put(self):
        """
        处理PUT请求
        """
        return self.handle_exception(self._handle_put)()

    def _handle_put(self):
        """
        处理PUT请求的内部方法
        """
        # 验证必需参数
        required_params = ["action", "data"]
        params = self.validate_params(required_params)
        if not params:
            return None

        action = params["action"]
        data = params["data"]

        logger.info(f"接收到PUT请求: action={action}")

        # 查询websocket客户端连接状态
        ws = self.get_ws()
        if not ws:
            return self.http_err("没有活跃的WebSocket连接")

        # 根据action执行不同操作
        if action == "update_config":
            # 更新配置
            try:
                ws.update_config(data)
                return self.http_success({"status": "updated"}, "配置已更新")
            except Exception as e:
                logger.error(f"更新配置失败: {str(e)}")
                return self.http_err(f"更新配置失败: {str(e)}")
        else:
            return self.http_err(f"不支持的action: {action}")

    def delete(self):
        """
        处理DELETE请求
        """
        return self.handle_exception(self._handle_delete)()

    def _handle_delete(self):
        """
        处理DELETE请求的内部方法
        """
        # 验证必需参数
        required_params = ["action", "id"]
        params = self.validate_params(required_params)
        if not params:
            return None

        action = params["action"]
        item_id = params["id"]

        logger.info(f"接收到DELETE请求: action={action}, id={item_id}")

        # 查询websocket客户端连接状态
        ws = self.get_ws()
        if not ws:
            return self.http_err("没有活跃的WebSocket连接")

        # 根据action执行不同操作
        if action == "remove_item":
            # 删除项目
            try:
                result = ws.remove_item(item_id)
                return self.http_success(result, "项目已删除")
            except Exception as e:
                logger.error(f"删除项目失败: {str(e)}")
                return self.http_err(f"删除项目失败: {str(e)}")
        else:
            return self.http_err(f"不支持的action: {action}")
