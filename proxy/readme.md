# Titan WebSocket代理服务器

这是Titan项目的WebSocket代理服务器模块，提供了高性能的WebSocket通信功能和HTTP代理服务。

## 功能特性

### WebSocket服务器 (WsProxy)
- 支持多连接模式
- 自定义消息处理
- 视频控制命令处理
- 状态同步
- 事件通知
- 自动心跳检测
- 消息队列异步处理
- 身份验证机制
- 消息广播与私聊
- 连接状态监控

### HTTP代理服务器 (HttpProxy)
- 支持GET/POST/PUT/DELETE请求
- 视频控制接口
- 配置更新
- 状态查询
- 异常处理
- WebSocket通信桥接

### WebSocket客户端
- 自动重连机制
- 消息处理器注册
- 心跳检测
- 消息队列
- 连接状态管理
- 异常处理

## 目录结构

```
proxy/
├── __init__.py          # 模块初始化
├── main.py             # 主程序入口
├── server/             # 服务器实现
│   ├── __init__.py
│   ├── http.py        # HTTP代理实现
│   ├── ws.py          # WebSocket代理实现
│   └── file.py        # 文件处理实现
├── client/            # 客户端实现
│   └── websocket.py   # WebSocket客户端
└── custom/            # 自定义组件
    └── wss.py         # 自定义WebSocket基类
```

## 使用方法

### 启动服务器

```python
from proxy.main import make_app
import tornado.ioloop

app = make_app()
app.listen(9000)
tornado.ioloop.IOLoop.current().start()
```

### WebSocket客户端示例

```python
from proxy.client.websocket import WebSocketClient

# 创建客户端实例
client = WebSocketClient(
    uri="ws://localhost:9000/api/websocket",
    auto_reconnect=True,
    reconnect_interval=3.0,
    ping_interval=30.0
)

# 注册消息处理器
@client.register_handler("video_status")
def handle_video_status(message):
    print(f"视频状态更新: {message}")

# 启动客户端
client.run()
```

### HTTP API接口

#### 视频控制
- GET `/api/control?action=play` - 播放视频
- GET `/api/control?action=pause` - 暂停视频
- GET `/api/control?action=stop` - 停止视频
- POST `/api/control` - 发送控制命令
  ```json
  {
    "action": "play",
    "video_path": "/path/to/video"
  }
  ```

#### WebSocket连接
- WS `/api/websocket` - WebSocket连接端点

## 配置选项

### 服务器配置
- `debug`: 是否启用调试模式
- `websocket_ping_interval`: WebSocket心跳间隔(秒)
- `websocket_ping_timeout`: WebSocket心跳超时(秒)
- `max_buffer_size`: 最大缓冲区大小
- `max_body_size`: 最大请求体大小

### 客户端配置
- `auto_reconnect`: 是否自动重连
- `reconnect_interval`: 重连间隔(秒)
- `max_reconnect_attempts`: 最大重连尝试次数
- `ping_interval`: 心跳间隔(秒)
- `ping_timeout`: 心跳超时(秒)
- `receive_timeout`: 接收消息超时(秒)

## 开发说明

### 消息格式
所有WebSocket消息都应该是JSON格式，包含以下字段：
- `type`: 消息类型
- `data`: 消息数据
- `timestamp`: 时间戳

示例：
```json
{
    "type": "video_command",
    "data": {
        "action": "play",
        "video_path": "/videos/example.mp4"
    },
    "timestamp": "2025-04-25T13:51:00Z"
}
```

### 状态码
- `success`: 操作成功
- `error`: 操作失败
- `warning`: 警告信息
- `info`: 普通信息
- `received`: 消息已接收

## 注意事项

1. 在生产环境中应该实现更严格的来源检查和安全措施
2. 建议使用SSL/TLS加密WebSocket连接
3. 需要适当配置心跳间隔以维持长连接
4. 建议实现消息重试机制以处理网络不稳定情况
5. 注意处理大文件传输的内存使用

## 依赖

- Python 3.8+
- Tornado
- websockets
- asyncio

## 许可证

MIT License
