"""
@Project ：Backend
@File    ：config.py
@Author  ：PySuper
@Date    ：2025/4/23 19:29
@Desc    ：Backend main.py
"""

import json

import requests

from algorithm import MathA, MathB, MathC
from config.algorithm import RESULT_SEND_URL
from decorators import log_exception, send_to_url

ALGORITHM_CONFIG = {
    "math-a": MathA,
    "math-b": MathB,
    "math-c": MathC,
}


class AlgorithmFactory:
    def __init__(self):
        self._instances = {}
        self._algorithms = ALGORITHM_CONFIG

    def create_algorithm(self, name):
        """
        根据算法名称创建算法实例（单例模式）
        @param name: 算法名称
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

    @log_exception
    # @log_execution_time
    # @log_function_call
    @send_to_url(url=RESULT_SEND_URL)  # 发送结果到指定url
    def execute_algorithm(self, algorithm_name, params):
        """
        执行算法
        @param algorithm_name: 算法名称
        @param params: 算法参数
        :return: 算法结果
        """
        algorithm = self.factory.create_algorithm(algorithm_name)
        result = algorithm.parse(params)
        # response = requests.post(url=RESULT_SEND_URL, json=json.dumps(result))
        # print(response.text)
        return {"status": "ok", "message": "A", "data": result}

    def main(self):
        # self.execute_algorithm("math-a", ParamsA(1))
        # self.execute_algorithm("math-b", ParamsB("11", "22"))
        # self.execute_algorithm("math-c", ParamsC([1], [1, 2], [1, 2, 3]))
        ...


# if __name__ == "__main__":
#     parse_math = Parse()
#     param = ParamsA(1)
#     url = "http://localhost:8080/result"
#     result = parse_math.execute_algorithm("math-a", param)
