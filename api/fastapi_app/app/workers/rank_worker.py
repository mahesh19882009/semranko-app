from rq import Worker

from app.queues.redis_client import get_redis


if __name__ == "__main__":
    redis_conn = get_redis()
    worker = Worker(["rank-check"], connection=redis_conn, default_job_timeout="600")
    worker.work(with_scheduler=False)
