"""上岗练 - 后端配置。"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 上岗练模型网关（OpenAI-compatible）
    model_provider: str = "mock"
    model_base_url: str = "https://api.deepseek.com"
    model_api_key: str = ""
    model_name: str = "deepseek-chat"
    model_timeout_seconds: int = 60
    model_max_retries: int = 1
    model_daily_budget: float = 20
    model_max_cost_per_call: float = 0.5
    demo_mode: bool = True
    training_max_revisions: int = 2
    training_max_model_calls: int = 6
    training_task_timeout_seconds: int = 90
    training_task_store: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    training_document_store: str = "memory"
    training_upload_prefix: str = "training-documents/"
    # DeepSeek
    deepseek_api_key: str = "sk-xxx"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Tavily (Web Search)
    tavily_api_key: str = ""
    enable_web_search: bool = False

    # DashScope (百炼 Embedding，用于知识库 RAG)
    dashscope_api_key: str = ""
    dashscope_embedding_model: str = "text-embedding-v4"
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 知识库 / 向量存储
    chroma_persist_dir: str = "./data/chroma"
    kb_upload_dir: str = "./data/uploads"
    kb_max_documents_per_user: int = 10
    kb_max_file_size_mb: int = 10
    kb_chunk_size: int = 1000
    kb_chunk_overlap: int = 150
    kb_retrieve_top_k: int = 4

    # 题目配图（DashScope 千问-文生图 qwen-image）
    dashscope_image_model: str = "qwen-image-2.0"
    # 生图专用 API Key（留空时回退使用 dashscope_api_key）。
    # 注意：部分 sk-ws- 开头的工作空间 Key 按用途限定权限范围，Embedding 与生图可能需要各自的 Key。
    dashscope_image_api_key: str = ""
    # 图像生成使用的原生 DashScope API 地址（与 OpenAI 兼容模式的 dashscope_base_url 不同）
    # 留空时会自动从 dashscope_base_url 派生（将 /compatible-mode/v1 替换为 /api/v1）
    dashscope_image_base_url: str = ""
    image_gen_size: str = "512*512"
    image_gen_daily_limit: int = 20
    image_gen_max_concurrency: int = 5

    # 腾讯云 COS（用于持久化存储 AI 生成的题目配图）
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_region: str = ""
    cos_bucket: str = ""
    cos_upload_prefix: str = "quiz-images/"
    # 可选：自定义访问域名（如 CDN 加速域名），留空则使用 COS 默认域名
    cos_domain: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True
    app_environment: str = "development"
    max_request_body_bytes: int = 10_500_000
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_generate: int = 10
    rate_limit_upload: int = 10
    rate_limit_login: int = 20
    rate_limit_answers: int = 30
    platform_store: str = "memory"
    cors_origins: str = "http://localhost:10086,http://127.0.0.1:10086"

    # JWT
    jwt_secret: str = "development-only-change-me-32-bytes"
    jwt_expire_minutes: int = 43200  # 30 天

    # 微信小程序
    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "zhiheng_health"
    mysql_charset: str = "utf8mb4"
    mysql_pool_minsize: int = 1
    mysql_pool_maxsize: int = 10
    # M0 核心流程不依赖数据库；需要旧功能时可在环境变量中开启。
    mysql_auto_init: bool = False
    mysql_connect_on_start: bool = False

    # Log
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_settings(settings: Settings) -> None:
    if settings.app_environment != "production": return
    errors = []
    if len(settings.jwt_secret.encode()) < 32 or settings.jwt_secret in {"change-me-in-production","development-only-change-me-32-bytes"}: errors.append("JWT_SECRET")
    if "*" in settings.cors_origins: errors.append("CORS_ORIGINS")
    if not settings.demo_mode and not settings.model_api_key: errors.append("MODEL_API_KEY")
    if settings.training_task_store != "redis": errors.append("TRAINING_TASK_STORE")
    if settings.training_document_store != "cos": errors.append("TRAINING_DOCUMENT_STORE")
    if settings.training_document_store == "cos" and not all([settings.cos_secret_id, settings.cos_secret_key, settings.cos_region, settings.cos_bucket]): errors.append("COS_CONFIG")
    if settings.platform_store != "mysql" or not settings.mysql_connect_on_start: errors.append("PLATFORM_STORE")
    if errors: raise RuntimeError("生产配置不安全: " + ", ".join(errors))
