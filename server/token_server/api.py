"""
@Project ：Titan
@File    ：platform.py
@Author  ：PySuper
@Date    ：2025/4/29 10:36
@Desc    ：Titan platform.py
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from model import Token, DataItem, User
from .utils import (
    fake_users_db,
    get_password_hash,
    create_access_token,
    authenticate_user,
    fake_data_db,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# 创建FastAPI应用
app = FastAPI(title="Titan API", description="Titan RESTful API服务")


# API路由
@app.post("/register", response_model=Token)
async def register(username: str, password: str, email: str):
    if username in fake_users_db:
        raise HTTPException(status_code=400, detail="用户名已存在")

    hashed_password = get_password_hash(password)
    user_dict = {"username": username, "email": email, "hashed_password": hashed_password, "disabled": False}
    fake_users_db[username] = user_dict

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/data", response_model=List[DataItem])
async def get_data(current_user: User = Depends(get_current_user)):
    return list(fake_data_db.values())


@app.post("/data", response_model=DataItem)
async def create_data(item: DataItem, current_user: User = Depends(get_current_user)):
    item.id = len(fake_data_db) + 1
    item.created_at = datetime.utcnow()
    item.updated_at = item.created_at
    fake_data_db[item.id] = item
    return item


@app.put("/data/{item_id}", response_model=DataItem)
async def update_data(item_id: int, item: DataItem, current_user: User = Depends(get_current_user)):
    if item_id not in fake_data_db:
        raise HTTPException(status_code=404, detail="数据不存在")

    item.id = item_id
    item.updated_at = datetime.utcnow()
    fake_data_db[item_id] = item
    return item


@app.delete("/data/{item_id}")
async def delete_data(item_id: int, current_user: User = Depends(get_current_user)):
    if item_id not in fake_data_db:
        raise HTTPException(status_code=404, detail="数据不存在")

    del fake_data_db[item_id]
    return {"message": "数据已删除"}
