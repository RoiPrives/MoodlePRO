import json

from redis.asyncio import Redis

JOB_QUEUE_KEY = "queue:jobs"
WORKER_HEARTBEAT_KEY = "worker:heartbeat"


def segment_channel(job_id: str) -> str:
    return f"job:{job_id}:segments"


async def publish_heartbeat(redis: Redis, ttl_seconds: int) -> None:
    """Refresh the worker liveness key on a TTL so the server knows a worker is alive."""
    await redis.set(WORKER_HEARTBEAT_KEY, "1", ex=ttl_seconds)


async def dequeue_job(redis: Redis, timeout: int = 5) -> str | None:
    result = await redis.blpop([JOB_QUEUE_KEY], timeout=timeout)
    if result is None:
        return None
    _, job_id = result
    return job_id.decode() if isinstance(job_id, bytes) else job_id


async def publish_segment(redis: Redis, job_id: str, text: str, start: float, end: float) -> None:
    payload = json.dumps(
        {"type": "segment", "job_id": job_id, "text": text, "start": start, "end": end}
    )
    await redis.publish(segment_channel(job_id), payload)
