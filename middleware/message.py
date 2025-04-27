"""
@Project ：Backend
@File    ：message.py
@Author  ：PySuper
@Date    ：2025/4/23 20:34
@Desc    ：处理消息中间件
"""

import threading
import time
from collections import deque
from queue import PriorityQueue
from typing import Any, List, Callable


class Message:
    def __init__(self, content: Any, priority: int = 0, timestamp: float = None):
        self.content = content
        self.priority = priority
        self.timestamp = timestamp or time.time()

    def __lt__(self, other):
        return self.priority > other.priority


class MessageMiddleware:
    """
    消息中间件

    1、基本的消息队列操作: 发送消息、获取消息、查看消息、清空消息队列等。
    2、优先级队列: 可以发送带优先级的消息,并通过get_priority_message()获取优先级最高的消息。
    3、消息订阅: 允许其他对象订阅消息,当有新消息时会通知所有订阅者。
    4、消息过滤: 可以根据条件筛选或移除消息。
    5、批量处理: 可以批量获取或处理所有消息。
    6、线程安全: 使用锁来确保在多线程环境下的安全操作。
    """

    def __init__(self):
        self._messages = deque()
        self._priority_queue = PriorityQueue()
        self._subscribers = []
        self._lock = threading.Lock()

    def send_message(self, message: Any, priority: int = 0):
        """
        发送消息
        @param message: 消息内容
        @param priority: 消息优先级 (越大优先级越高)
        """
        with self._lock:
            msg = Message(message, priority)
            self._messages.append(msg)
            self._priority_queue.put(msg)
        self._notify_subscribers(msg)

    def get_message(self) -> Any:
        """
        获取下一条消息 (FIFO顺序)
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._messages.popleft().content if self._messages else None

    def get_priority_message(self) -> Any:
        """
        获取下一条优先级最高的消息
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._priority_queue.get().content if not self._priority_queue.empty() else None

    def peek_message(self) -> Any:
        """
        查看下一条消息但不移除
        :return: 消息内容，如果队列为空则返回None
        """
        with self._lock:
            return self._messages[0].content if self._messages else None

    def get_all_messages(self) -> List[Any]:
        """
        获取所有消息
        :return: 消息列表
        """
        with self._lock:
            messages = [msg.content for msg in self._messages]
            self._messages.clear()
            while not self._priority_queue.empty():
                self._priority_queue.get()
        return messages

    def clear_messages(self):
        """
        清空消息队列
        """
        with self._lock:
            self._messages.clear()
            while not self._priority_queue.empty():
                self._priority_queue.get()

    def message_count(self) -> int:
        """
        获取消息数量
        :return: 消息数量
        """
        return len(self._messages)

    def subscribe(self, callback: Callable[[Message], None]):
        """
        订阅消息
        @param callback: 接收消息的回调函数
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Message], None]):
        """
        取消订阅
        @param callback: 要取消的回调函数
        """
        self._subscribers.remove(callback)

    def _notify_subscribers(self, message: Message):
        """
        通知所有订阅者
        @param message: 要广播的消息
        """
        for subscriber in self._subscribers:
            subscriber(message)

    def filter_messages(self, condition: Callable[[Any], bool]) -> List[Any]:
        """
        根据条件筛选消息
        @param condition: 筛选条件函数
        :return: 符合条件的消息列表
        """
        with self._lock:
            return [msg.content for msg in self._messages if condition(msg.content)]

    def remove_messages(self, condition: Callable[[Any], bool]):
        """
        根据条件移除消息
        @param condition: 移除条件函数
        """
        with self._lock:
            self._messages = deque([msg for msg in self._messages if not condition(msg.content)])
            new_priority_queue = PriorityQueue()
            while not self._priority_queue.empty():
                msg = self._priority_queue.get()
                if not condition(msg.content):
                    new_priority_queue.put(msg)
            self._priority_queue = new_priority_queue

    def process_messages(self, processor: Callable[[Any], None]):
        """
        处理所有消息
        @param processor: 处理消息的函数
        """
        while True:
            message = self.get_message()
            if message is None:
                break
            processor(message)


# 使用示例:
# middleware = MessageMiddleware()
# middleware.send_message("Hello", priority=1)
# middleware.send_message("World", priority=2)
# print(middleware.get_priority_message())  # 输出: World
# print(middleware.get_message())  # 输出: Hello
