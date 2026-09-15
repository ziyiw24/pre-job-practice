"""上岗练 M0 任务存储：单进程内存 + TTL + 幂等键。"""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.training import TrainingAgentInfo, TrainingQuiz


@dataclass
class TrainingTask:
    task_id: str
    client_request_id: str
    status: str
    progress_stage: str
    created_at: datetime
    expires_at: datetime
    result: TrainingQuiz | None = None
    error_code: str | None = None
    error_message: str | None = None
    agent: TrainingAgentInfo | None = None


class InMemoryTrainingTaskStore:
    def __init__(self, ttl_seconds: int = 1800):
        self.ttl_seconds = ttl_seconds
        self._tasks: dict[str, TrainingTask] = {}
        self._request_ids: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_or_get(self, task_id: str, client_request_id: str) -> tuple[TrainingTask, bool]:
        async with self._lock:
            self._cleanup()
            known_task_id = self._request_ids.get(client_request_id)
            if known_task_id and known_task_id in self._tasks:
                return self._tasks[known_task_id], False
            now = datetime.now(timezone.utc)
            task = TrainingTask(
                task_id=task_id,
                client_request_id=client_request_id,
                status="pending",
                progress_stage="reading",
                created_at=now,
                expires_at=now + timedelta(seconds=self.ttl_seconds),
            )
            self._tasks[task_id] = task
            self._request_ids[client_request_id] = task_id
            return task, True

    async def get(self, task_id: str) -> TrainingTask | None:
        async with self._lock:
            self._cleanup()
            return self._tasks.get(task_id)

    async def update(self, task_id: str, **changes) -> TrainingTask | None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            for key, value in changes.items():
                setattr(task, key, value)
            return task

    def _cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [task_id for task_id, task in self._tasks.items() if task.expires_at <= now]
        for task_id in expired:
            task = self._tasks.pop(task_id)
            self._request_ids.pop(task.client_request_id, None)


training_task_store = InMemoryTrainingTaskStore()


class RedisTrainingTaskStore:
    def __init__(self, url: str, ttl_seconds: int = 1800):
        from redis.asyncio import from_url
        self.redis = from_url(url, decode_responses=True); self.ttl_seconds = ttl_seconds

    async def create_or_get(self, task_id: str, client_request_id: str):
        now=datetime.now(timezone.utc); task=TrainingTask(task_id,client_request_id,"pending","reading",now,now+timedelta(seconds=self.ttl_seconds))
        # 两个 key 必须原子创建，避免多实例竞争时看到幂等 key 却读不到任务。
        result=await self.redis.eval(
            "local known=redis.call('GET',KEYS[1]); "
            "if known then return {known,'0'} end; "
            "redis.call('SET',KEYS[2],ARGV[2],'EX',ARGV[3]); "
            "redis.call('SET',KEYS[1],ARGV[1],'EX',ARGV[3]); return {ARGV[1],'1'}",
            2,f"training:idempotency:{client_request_id}",f"training:task:{task_id}",
            task_id,self._dump(task),self.ttl_seconds,
        )
        resolved_id, created=result[0],result[1]=="1"
        resolved=task if created else await self.get(resolved_id)
        if resolved is None:raise RuntimeError("TASK_STORE_INCONSISTENT")
        return resolved,created

    async def get(self, task_id: str):
        raw=await self.redis.get(f"training:task:{task_id}")
        if not raw:return None
        data=json.loads(raw); data["created_at"]=datetime.fromisoformat(data["created_at"]); data["expires_at"]=datetime.fromisoformat(data["expires_at"])
        if data.get("result"):data["result"]=TrainingQuiz.model_validate(data["result"])
        if data.get("agent"):data["agent"]=TrainingAgentInfo.model_validate(data["agent"])
        return TrainingTask(**data)

    async def update(self, task_id: str, **changes):
        task=await self.get(task_id)
        if not task:return None
        for key,value in changes.items():setattr(task,key,value)
        await self.redis.set(f"training:task:{task_id}",self._dump(task),ex=self.ttl_seconds); return task

    @staticmethod
    def _dump(task):
        data=task.__dict__.copy(); data["created_at"]=data["created_at"].isoformat(); data["expires_at"]=data["expires_at"].isoformat()
        if data.get("result"):data["result"]=data["result"].model_dump()
        if data.get("agent"):data["agent"]=data["agent"].model_dump()
        return json.dumps(data,ensure_ascii=False)


@lru_cache
def get_training_task_store():
    from app.core.config import get_settings
    settings=get_settings()
    return RedisTrainingTaskStore(settings.redis_url) if settings.training_task_store == "redis" else training_task_store
