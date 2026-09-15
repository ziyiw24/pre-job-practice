from __future__ import annotations
import asyncio, hashlib, time
from collections import defaultdict, deque
from fastapi import Request
from app.core.config import get_settings

_events: dict[str, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()

def _rule(path: str):
    s=get_settings()
    if path.endswith("/training/generate/async"): return "generate",s.rate_limit_generate
    if path.endswith("/training/documents"): return "upload",s.rate_limit_upload
    if path.endswith("/user/login"): return "login",s.rate_limit_login
    if "/employee/assignments/" in path and path.endswith("/answers"): return "answers",s.rate_limit_answers
    return None

async def allow_request(request: Request) -> bool:
    settings=get_settings(); rule=_rule(request.url.path)
    if not settings.rate_limit_enabled or not rule:return True
    name,limit=rule; raw=(request.client.host if request.client else "unknown")
    identity=hashlib.sha256(raw.encode()).hexdigest()[:20]; key=f"rate:{name}:{identity}"; now=time.time()
    if settings.training_task_store == "redis":
        from redis.asyncio import from_url
        client=from_url(settings.redis_url,decode_responses=True); bucket=int(now//settings.rate_limit_window_seconds)
        redis_key=f"{key}:{bucket}"; count=await client.incr(redis_key)
        if count==1:await client.expire(redis_key,settings.rate_limit_window_seconds+1)
        await client.aclose(); return count<=limit
    async with _lock:
        events=_events[key]; cutoff=now-settings.rate_limit_window_seconds
        while events and events[0]<cutoff:events.popleft()
        if len(events)>=limit:return False
        events.append(now); return True
