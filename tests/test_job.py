import asyncio
import time

import pytest

from executor.engine.core import Engine, EngineSetting
from executor.engine.job import LocalJob, ThreadJob, ProcessJob
from executor.engine.job.base import InvalidStateError
from executor.engine.job.condition import AfterAnother, AllSatisfied


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
        with pytest.raises(InvalidStateError):
            await job.emit()

    asyncio.run(submit_job())

    async def submit_job():
        with pytest.raises(InvalidStateError):
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
            job.result()
        await engine.submit_async(job)
        with pytest.raises(InvalidStateError):
            job.result()

    asyncio.run(submit_job())


def test_job_retry():
    def raise_exception():
        print("try")
        raise ValueError("error")
    job = ProcessJob(
        raise_exception, retries=2,
        retry_time_delta=1)
    assert job.retry_remain == 2
    setting = EngineSetting(print_traceback=False)
    engine = Engine(setting=setting)
    with engine:
        engine.submit(job)
        time.sleep(5)
    assert job.retry_remain == 0


def test_dependency():
    def add(a, b):
        return a + b

    with Engine() as engine:
        job1 = ProcessJob(add, (1, 2))
        job2 = ProcessJob(add, (job1.future, 3))
        engine.submit(job1, job2)
        engine.wait_job(job2)
        assert job2.result() == 6


def test_dependency_2():
    def add(a, b):
        return a + b

    with Engine() as engine:
        job1 = ProcessJob(add, (1, 2))
        job2 = ProcessJob(add, (job1.future, 3))
        job3 = ProcessJob(
            add, kwargs={"a": job2.future, "b": 4},
            condition=AfterAnother(job_id=job1.id)
        )
        engine.submit(job3, job2, job1)
        assert isinstance(job3.condition, AllSatisfied)
        engine.wait_job(job3)
        assert job3.result() == 10


def test_upstream_failed():
    def add(a, b):
        return a + b

    def raise_exception():
        raise ValueError("error")

    with Engine() as engine:
        job1 = ProcessJob(raise_exception)
        job2 = ProcessJob(add, (1, job1.future))
        engine.submit(job2, job1)
        engine.wait()
        assert job1.status == "failed"
        assert job2.status == "cancelled"


def test_upstream_cancel():
    def add(a, b):
        time.sleep(3)
        return a + b

    with Engine() as engine:
        job1 = ProcessJob(add, (1, 2))
        job2 = ProcessJob(add, (1, job1.future))
        engine.submit(job2, job1)
        engine.cancel(job1)
        engine.wait()
        assert job1.status == "cancelled"
        assert job2.status == "cancelled"
