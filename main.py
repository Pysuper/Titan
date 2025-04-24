"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 19:29
@Desc    ：Backend main.py
"""
import json
import time

import requests
from requests.exceptions import RequestException

from algorithm import MathA, MathB, MathC, ParamsA


class AlgorithmFactory:
    def __init__(self):
        self._instances = {}
        self._algorithms = {
            "math-a": MathA,
            "math-b": MathB,
            "math-c": MathC,
        }

    def create_algorithm(self, name):
        """
        根据算法名称创建算法实例（单例模式）
        :param name: 算法名称
        :return: 算法实例（单例模式）
        """
        if name not in self._instances:
            algorithm_class = self._algorithms.get(name)
            if algorithm_class:
                self._instances[name] = algorithm_class()
            else:
                raise ValueError(f"未知的算法名称: {name}")
        return self._instances[name]


class Parse:
    def __init__(self):
        self.factory = AlgorithmFactory()
        self.main()

    def execute_algorithm(self, algorithm_name, params):
        """
        执行算法
        :param algorithm_name: 算法名称
        :param params: 算法参数
        :return: 算法结果
        """
        algorithm = self.factory.create_algorithm(algorithm_name)
        result = algorithm.parse(params)
        print(result.a)

    def main(self):
        # self.execute_algorithm("math-a", ParamsA(1))
        # self.execute_algorithm("math-b", ParamsB("11", "22"))
        # self.execute_algorithm("math-c", ParamsC([1], [1, 2], [1, 2, 3]))
        ...

    def send_result(self, result, url):
        """
        使用POST请求，将算法结果发送到指定服务器，自动重连3次
        :param result: 结果
        :param url: 目标服务器URL
        :return: 发送状态：True/False
        """

        # 最大重试次数
        max_retries = 3
        # 重试间隔（秒）
        retry_interval = 2
        # 超时设置（秒）
        timeout = 10

        # 尝试将结果转换为JSON
        try:
            if hasattr(result, "__dict__"):
                # 如果结果是对象，尝试转换其属性为字典
                payload = result.__dict__
            elif isinstance(result, dict):
                # 如果已经是字典，直接使用
                payload = result
            else:
                # 尝试使用json序列化
                payload = json.loads(json.dumps(result))
        except (TypeError, json.JSONDecodeError) as e:
            print(f"结果序列化失败: {str(e)}")
            return False

        # 添加时间戳
        payload["timestamp"] = time.time()

        # 设置请求头
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # 重试逻辑
        for attempt in range(1, max_retries + 1):
            try:
                print(f"正在发送结果到 {url}，第 {attempt} 次尝试...")
                response = requests.post(url=url, json=payload, headers=headers, timeout=timeout)

                # 检查响应状态码
                if response.status_code in (200, 201, 202):
                    try:
                        response_data = response.json()
                        print(f"发送成功，服务器响应: {response_data}")
                        return True
                    except json.JSONDecodeError:
                        print(f"发送成功，但服务器响应不是有效的JSON: {response.text}")
                        return True
                else:
                    print(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")

                    # 如果是最后一次尝试，返回失败
                    if attempt == max_retries:
                        return False

                    # 否则等待后重试
                    time.sleep(retry_interval)

            except RequestException as e:
                print(f"请求异常: {str(e)}")

                # 如果是最后一次尝试，返回失败
                if attempt == max_retries:
                    return False

                # 否则等待后重试
                print(f"将在 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

        # 如果所有尝试都失败
        return False


if __name__ == "__main__":
    parse_math = Parse()
    param = ParamsA(1)
    url = "http://localhost:8080/result"
    result = parse_math.execute_algorithm("math-a", param)
