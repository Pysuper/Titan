"""
@Project ：Backend
@File    ：__init__.py.py
@Author  ：PySuper
@Date    ：2025/4/23 19:40
@Desc    ：算法模块
"""

from .mathA.main import MathA
from .mathA.params import ParamsA
from .mathB.main import MathB
from .mathB.params import ParamsB
from .mathC.main import MathC
from .mathC.params import ParamsC

__all__ = [
    "MathA",
    "MathB",
    "MathC",
    "ParamsA",
    "ParamsB",
    "ParamsC",
]
