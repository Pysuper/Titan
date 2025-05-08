# Python实现分布式计算

分布式计算是将计算任务分配到多台计算机上并行执行的技术。Python提供了多种方式来实现分布式计算，下面介绍几种常见的方法。

## 1. 使用multiprocessing模块

Python内置的`multiprocessing`模块可以轻松实现多进程计算，适合单机多核的分布式计算。

```python
from multiprocessing import Pool

def square(x):
    return x * x

if __name__ == '__main__':
    with Pool(4) as p:  # 使用4个进程
        results = p.map(square, range(10))
    print(results)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

## 2. 使用Celery分布式任务队列

Celery是一个强大的分布式任务队列系统，适合跨多台机器的分布式计算。

```python
# tasks.py
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@localhost//')

@app.task
def add(x, y):
    return x + y

# 启动worker: celery -A tasks worker --loglevel=info

# 调用任务
result = add.delay(4, 4)
print(result.get())  # 获取结果
```

## 3. 使用Dask

Dask是一个灵活的并行计算库，可以扩展到分布式集群。

```python
import dask
from dask.distributed import Client

client = Client()  # 连接到本地集群

def process_data(x):
    # 复杂计算
    return x ** 2

# 创建延迟计算
lazy_results = [dask.delayed(process_data)(x) for x in range(10)]

# 并行计算
results = dask.compute(*lazy_results)
print(results)  # (0, 1, 4, 9, 16, 25, 36, 49, 64, 81)
```

## 4. 使用Ray

Ray是一个高性能的分布式执行框架。

```python
import ray

ray.init()

@ray.remote
def f(x):
    return x * x

futures = [f.remote(i) for i in range(4)]
print(ray.get(futures))  # [0, 1, 4, 9]
```

## 5. 使用PySpark

PySpark是Apache Spark的Python API，适合大规模数据处理。

```python
from pyspark import SparkContext

sc = SparkContext("local", "Distributed App")

data = sc.parallelize(range(10))
result = data.map(lambda x: x * x).collect()

print(result)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

## 6. 使用MPI (通过mpi4py)

MPI (Message Passing Interface) 是高性能计算的标准。

```python
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

if rank == 0:
    data = {'a': 7, 'b': 3.14}
    comm.send(data, dest=1, tag=11)
elif rank == 1:
    data = comm.recv(source=0, tag=11)
    print(f"Received data: {data}")
```

## 选择建议

- 单机多核: `multiprocessing` 或 `concurrent.futures`
- 分布式任务队列: `Celery`
- 大数据处理: `PySpark` 或 `Dask`
- 通用分布式计算: `Ray`
- 高性能计算: `mpi4py` (MPI)

每种工具都有其适用场景，根据你的具体需求选择合适的工具。
