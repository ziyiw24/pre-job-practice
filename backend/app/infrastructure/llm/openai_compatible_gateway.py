"""OpenAI-compatible 结构化输出适配器。"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import Settings, get_settings

_local_budget_cents: dict[str,int] = {}


class ModelGatewayError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class OpenAICompatibleGateway:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def generate_structured(self, *, system_prompt: str, user_prompt: str,
                                  output_schema: type, temperature: float = 0.2,
                                  timeout_seconds: int | None = None, context: dict | None = None) -> Any:
        await self._reserve_budget()
        model = ChatOpenAI(
            model=self.settings.model_name, base_url=self.settings.model_base_url,
            api_key=self.settings.model_api_key, temperature=temperature,
            timeout=timeout_seconds or self.settings.model_timeout_seconds,
            max_retries=self.settings.model_max_retries,
        ).with_structured_output(output_schema)
        try:
            return await asyncio.wait_for(
                model.ainvoke([("system", system_prompt), ("human", user_prompt + "\n<context>\n" + json.dumps(context or {}, ensure_ascii=False) + "\n</context>")]),
                timeout=timeout_seconds or self.settings.model_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ModelGatewayError("MODEL_TIMEOUT", "模型响应超时") from exc
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            code = "MODEL_RATE_LIMITED" if status == 429 else "MODEL_UNAVAILABLE"
            raise ModelGatewayError(code, "模型服务暂时不可用") from exc

    async def _reserve_budget(self):
        """按单次费用上限预留当日预算，宁可提前停止也不超支。"""
        cents=max(1,round(self.settings.model_max_cost_per_call*100));limit=round(self.settings.model_daily_budget*100)
        if self.settings.training_task_store=="redis":
            from redis.asyncio import from_url
            client=from_url(self.settings.redis_url,decode_responses=True);key=f"budget:model:{date.today().isoformat()}";value=await client.incrby(key,cents)
            if value==cents:await client.expire(key,172800)
            await client.aclose()
            if value>limit:raise ModelGatewayError("MODEL_BUDGET_EXCEEDED","当日模型预算已用完")
        else:
            key=date.today().isoformat();_local_budget_cents[key]=_local_budget_cents.get(key,0)+cents
            if _local_budget_cents[key]>limit:raise ModelGatewayError("MODEL_BUDGET_EXCEEDED","当日模型预算已用完")


class FakeModelGateway:
    def __init__(self, responses: list[Any]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise ModelGatewayError("MODEL_OUTPUT_INVALID", "fake response exhausted")
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        schema = kwargs["output_schema"]
        return value if isinstance(value, BaseModel) else schema.model_validate(value)
