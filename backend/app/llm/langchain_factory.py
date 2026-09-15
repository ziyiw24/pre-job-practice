"""LangChain ChatOpenAI 工厂"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def is_chat_model_configured() -> bool:
    key = get_settings().deepseek_api_key.strip()
    return bool(key and key not in {"sk-xxx", "change-me"})


@lru_cache()
def get_chat_model(temperature: float = 0.4) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        temperature=temperature,
        max_tokens=4096,
    )
