from rq import Queue
from app.queues.redis_client import get_redis

def get_backlink_check_queue() -> Queue:
    return Queue("backlink-check", connection=get_redis())