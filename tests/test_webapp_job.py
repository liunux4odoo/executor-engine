import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler

from executor.engine.core import Engine
from executor.engine.job.extend.webapp import WebAppJob


def run_simple_httpd(ip: str, port: int):
    server_addr = (ip, port)
    httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
    httpd.serve_forever()


def test_run_webapp():
    engine = Engine()

    async def submit_job():
        job = WebAppJob(run_simple_httpd, ip="127.0.0.1", port=8001, check_delta=0.5)
        await engine.submit(job)
        await asyncio.sleep(4)
        assert job.status == "running"
        await job.cancel()
        assert job.status == "canceled"

    asyncio.run(submit_job())


def test_port_check():
    engine = Engine()

    def run_error_httpd(ip: str, port: int):
        server_addr = (ip, port + 1)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    async def submit_job():
        job = WebAppJob(run_error_httpd, ip="127.0.0.1", port=8002, check_delta=0.5)
        await engine.submit(job)
        await asyncio.sleep(4)
        assert job.status == "failed"

    asyncio.run(submit_job())
