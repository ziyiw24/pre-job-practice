from datetime import datetime, timezone

import pytest

from app.repositories.training_task_store import RedisTrainingTaskStore


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def eval(self, _script, _count, idem, task_key, task_id, payload, _ttl):
        if idem in self.values:
            return [self.values[idem], "0"]
        self.values[task_key] = payload
        self.values[idem] = task_id
        return [task_id, "1"]

    async def get(self, key):
        return self.values.get(key)


@pytest.mark.asyncio
async def test_redis_idempotency_returns_one_atomic_task():
    store = object.__new__(RedisTrainingTaskStore)
    store.redis = FakeRedis()
    store.ttl_seconds = 1800
    first, created = await store.create_or_get("task_1", "request_1")
    second, created_again = await store.create_or_get("task_2", "request_1")
    assert created is True and created_again is False
    assert first.task_id == second.task_id == "task_1"
    assert isinstance(second.created_at, datetime) and second.created_at.tzinfo == timezone.utc
