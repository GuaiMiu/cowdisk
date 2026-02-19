"""
@File: io_pool.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: I/O 线程池
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Lock
from typing import Callable, TypeVar


_T = TypeVar("_T")
_pool_lock = Lock()
_executor: ThreadPoolExecutor | None = None
_executor_size = 0


def get_io_executor(max_workers: int) -> ThreadPoolExecutor:
    global _executor, _executor_size
    with _pool_lock:
        if _executor is None or _executor_size != max_workers:
            if _executor is not None:
                _executor.shutdown(wait=False)
            _executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="io-pool",
            )
            _executor_size = max_workers
    return _executor


async def run_io(max_workers: int, func: Callable[..., _T], *args, **kwargs) -> _T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        get_io_executor(max_workers),
        partial(func, *args, **kwargs),
    )
