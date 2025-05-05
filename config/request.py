"""
@Project ：Titan
@File    ：request.py
@Author  ：PySuper
@Date    ：2025/4/24 14:22
@Desc    ：Titan request.py
"""

import dataclasses


# TODO: 考虑如何将这些参数，传递到运行的方法中


@dataclasses.dataclass
class SendResult:
    """
    发送结果
    """

    max_retries: int
    retry_interval: int
    timeout: int
