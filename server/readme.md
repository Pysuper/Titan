# Titan 服务器模块

这是Titan项目的服务器模块，包含多个独立的服务组件，提供不同的API功能。

## 目录结构

```
server/
├── __init__.py           # 模块初始化
├── only_post/           # 仅POST请求API服务
│   ├── __init__.py
│   ├── api.py          # API接口定义
│   ├── main.py         # 主程序入口
│   ├── models.py       # 数据模型
│   └── util.py         # 工具函数
└── token_server/       # Token认证服务
    ├── __init__.py
    ├── api.py         # API接口定义
    ├── model.py       # 数据模型
    └── utils.py       # 工具函数
```

## 服务组件

### 1. Only POST API服务 (only_post)

专门用于处理POST请求的FastAPI服务。

#### 特性
- 仅接受POST请求
- 全局异常处理
- 健康检查接口
- 任务处理和结果返回

#### API端点
- POST `/api/task` - 任务提交接口
- POST `/api/result` - 结果获取接口
- POST `/health` - 健康检查接口

#### 使用方法
```python
from server.only_post.main import start_server

# 启动服务器
start_server(host="localhost", port=9003)
```

### 2. Token认证服务 (token_server)

提供基于OAuth2的用户认证和数据管理服务。

#### 特性
- JWT Token认证
- 用户注册和登录
- 数据CRUD操作
- 访问控制

#### API端点
- POST `/register` - 用户注册
  ```json
  {
    "username": "string",
    "password": "string",
    "email": "string"
  }
  ```

- POST `/token` - 获取访问令牌
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```

- GET `/data` - 获取数据列表
- POST `/data` - 创建新数据
- PUT `/data/{item_id}` - 更新数据
- DELETE `/data/{item_id}` - 删除数据

#### 认证流程
1. 用户注册或登录获取访问令牌
2. 在后续请求中使用Bearer认证头
3. 令牌有效期为30分钟

## 配置说明

### Only POST服务
- 默认端口：9003
- 日志配置：使用项目统一logger
- 异常处理：全局异常处理器

### Token服务
- 访问令牌过期时间：30分钟
- 密码加密：使用哈希加密
- 数据存储：当前使用内存存储（可扩展到数据库）

## 开发指南

### 添加新的API端点
1. 在相应服务的api.py中定义新的路由
2. 在models.py中添加需要的数据模型
3. 实现相应的处理逻辑
4. 更新文档

### 错误处理
- 使用HTTPException处理HTTP错误
- 实现自定义异常处理器
- 返回统一的错误响应格式

## 依赖

- FastAPI
- Uvicorn
- Python-Jose (JWT)
- Passlib (密码哈希)
- Pydantic (数据验证)

## 部署

### 开发环境
```bash
uvicorn server.only_post.main:app --reload --port 9003
```

### 生产环境
```bash
uvicorn server.only_post.main:app --host 0.0.0.0 --port 9003 --workers 4
```

## 注意事项

1. Token服务在生产环境中应使用安全的密钥存储
2. 建议使用HTTPS保护API通信
3. 实现适当的速率限制和访问控制
4. 考虑使用数据库替代内存存储
5. 定期更新依赖包以修复安全漏洞

## 许可证

MIT License
