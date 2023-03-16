import asyncio
import traceback

import pytest

from executor.engine.core import Engine
from executor.engine.job import LocalJob, ThreadJob, ProcessJob
from executor.engine.manager import Jobs, JobStore


test_job_cls = [LocalJob, ThreadJob, ProcessJob]


def test_jobs_cache():
    engine = Engine()

    async def submit_job():
        for job_cls in test_job_cls:
            job = job_cls(
                lambda x: x**2, (2,),
                error_callback=lambda err: traceback.print_exc())
            await engine.submit(job)
        await engine.wait()

    asyncio.run(submit_job())
    assert len(engine.jobs.done.cache) == 3

    old_path = engine.jobs.cache_path
    jobs = Jobs(old_path)
    assert len(jobs.done.cache) == 3
    jobs.update_from_cache()
    assert len(jobs.done) == 3
    assert len(jobs.done.keys()) == 3
    assert len(jobs.done.items()) == 3
    job_id_0 = jobs.done.keys()[0]
    assert job_id_0 in jobs
    jobs.set_engine(engine)
    job0 = jobs.get_job_by_id(job_id_0)
    assert job0.status == 'done'
    jobs.move_job_store(job0, 'done')
    assert job0.engine is engine
    jobs.clear_non_active()
    assert len(jobs.done) == 0
    jobs.clear_all()
    assert len(jobs.all_jobs()) == 0

    store = JobStore(None)
    with pytest.raises(RuntimeError):
        store.get_from_cache('test')

