"""模型供应商端口：业务层只依赖这个协议。"""
from typing import Any, Protocol


class ModelGateway(Protocol):
    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str, output_schema: type,
        temperature: float = 0.2, timeout_seconds: int = 60,
        context: dict | None = None,
    ) -> Any: ...
