import asyncio
import time

import pytest

from executor.engine.core import Engine
from executor.engine.job import LocalJob, ThreadJob, ProcessJob
from executor.engine.job.base import get_callable_name
from executor.engine.job.base import JobEmitError, InvalidStateError


def test_corner_cases():
    job = LocalJob(lambda x: x**2, (2,))
    assert job.has_resource() is False
    assert job.consume_resource() is False
    assert job.release_resource() is False

    job = ThreadJob(lambda x: x**2, (2,))
    assert job.has_resource() is False
    assert job.consume_resource() is False
    assert job.release_resource() is False

    job = ProcessJob(lambda x: x**2, (2,))
    assert job.has_resource() is False
    assert job.consume_resource() is False
    assert job.release_resource() is False
    assert job.runnable() is False
    assert job.cache_dir is None

    async def submit_job():
        with pytest.raises(JobEmitError):
            await job.emit()

    asyncio.run(submit_job())

    async def submit_job():
        with pytest.raises(JobEmitError):
            await job.rerun()

    asyncio.run(submit_job())

    async def submit_job():
        with pytest.raises(InvalidStateError):
            await job.join()

    asyncio.run(submit_job())


def test_result_fetch_error():
    def sleep_2s():
        time.sleep(2)

    job = ProcessJob(sleep_2s)

    engine = Engine()

    async def submit_job():
        with pytest.raises(InvalidStateError):
            await job.result()
        await engine.submit_async(job)
        with pytest.raises(InvalidStateError):
            await job.result()

    asyncio.run(submit_job())


def test_job_retry():
    def raise_exception():
        print("try")
        raise ValueError("error")
    job = ProcessJob(
        raise_exception, retries=2,
        retry_time_delta=1)
    assert job.retry_count == 0
    engine = Engine()
    with engine:
        engine.submit(job)
        time.sleep(5)
    assert job.retry_count == 2


def test_get_callable_name():
    def a():
        pass

    assert get_callable_name(a) == "a"

    class A():
        def __call__(self):
            pass

    assert get_callable_name(A()) == "A"

    class B():
        def __init__(self, func):
            self.func = func

    assert get_callable_name(B(a)) == "a"