from rq import Queue

from app.queues.redis_client import get_redis


def get_rank_check_queue() -> Queue:
    return Queue("rank-check", connection=get_redis())
