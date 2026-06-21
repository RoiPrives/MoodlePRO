from httpx import ASGITransport, AsyncClient

import client
from app.main import app
from app.services.queue import WORKER_HEARTBEAT_KEY, worker_is_alive
from config import WorkerSettings


async def test_worker_heartbeat_over_http_marks_worker_alive(fake_redis):
    """The worker posts its heartbeat to the server over HTTPS (it can't reach Redis from
    the cluster); the server SETs the liveness key the Groq-fallback routing reads."""
    await fake_redis.delete(WORKER_HEARTBEAT_KEY)  # fakeredis shares state across tests by URL

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as server_client:
            assert await worker_is_alive(fake_redis) is False

            worker_settings = WorkerSettings(internal_api_token="test-internal-token")
            await client.post_heartbeat(server_client, worker_settings, ttl=30)

            assert await worker_is_alive(fake_redis) is True
            ttl = await fake_redis.ttl(WORKER_HEARTBEAT_KEY)
            assert 0 < ttl <= 30


async def test_heartbeat_requires_the_internal_token(fake_redis):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as server_client:
            resp = await server_client.post("/internal/worker/heartbeat", params={"ttl": 30})
            assert resp.status_code == 401
