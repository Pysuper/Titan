# -*- coding:utf-8 -*-
"""
@Project ：Titan
@File    ：system.py
@Author  ：PySuper
@Date    ：2025-04-26 08:44
@Desc    ：Titan system
"""

import platform
import subprocess


def close_port(port, logger):
    """
    关闭指定端口号的进程
    @param port: 需要关闭的端口号
    @return: 是否成功关闭端口
    """
    # 验证端口参数
    try:
        port = int(port)
        if port < 0 or port > 65535:
            logger.error(f"无效的端口号: {port}，端口范围应为 0-65535")
            return False
    except (ValueError, TypeError):
        logger.error(f"端口号必须为整数: {port}")
        return False

    try:
        system = platform.system().lower()

        # 根据不同操作系统选择不同处理方式
        if system == "windows":
            return _close_port_windows(port, logger)
        elif system in ("linux", "darwin"):  # Linux 和 macOS
            return _close_port_unix(port, logger)
        else:
            logger.error(f"不支持的操作系统: {system}")
            return False
    except Exception as e:
        logger.error(f"关闭端口 {port} 时发生未知错误: {e}")
        return False


def _close_port_windows(port, logger):
    """
    在 Windows 系统上关闭指定端口
    @param port: 需要关闭的端口号
    @return: 是否成功关闭端口
    """
    try:
        # 使用列表参数避免命令注入
        cmd_find = ["netstat", "-ano"]
        result = subprocess.run(cmd_find, capture_output=True, text=True, shell=False)

        if result.returncode != 0:
            logger.debug(f"端口 {port} 没有找到相关进程")
            return False

        found = False
        for line in result.stdout.strip().split("\n"):
            if f":{port}" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/PID", pid, "/F"], shell=False)
                    logger.debug(f"已终止使用端口 {port} 的进程 (PID: {pid})")
                    found = True

        if not found:
            logger.debug(f"端口 {port} 没有找到相关进程")
            return False
        return found
    except subprocess.SubprocessError as e:
        logger.debug(f"端口 {port} 没有找到相关进程: {e}")
        return False


def _close_port_unix(port, logger):
    """
    在 Unix-like 系统 (Linux/macOS) 上关闭指定端口
    @param port: 需要关闭的端口号
    @return: 是否成功关闭端口
    """
    try:
        # 使用列表参数避免命令注入
        cmd_find = ["lsof", "-i", f":{port}"]
        result = subprocess.run(cmd_find, capture_output=True, text=True, shell=False)

        if result.returncode != 0:
            logger.debug(f"端口 {port} 没有找到相关进程")
            return False

        found = False
        for line in result.stdout.strip().split("\n")[1:]:  # 跳过标题行
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                subprocess.run(["kill", "-9", pid], shell=False)
                logger.debug(f"已终止使用端口 {port} 的进程 (PID: {pid})")
                found = True

        if not found:
            logger.debug(f"端口 {port} 没有找到相关进程")
            return False
        return found
    except subprocess.SubprocessError as e:
        logger.debug(f"端口 {port} 没有找到相关进程: {e}")
        return False
