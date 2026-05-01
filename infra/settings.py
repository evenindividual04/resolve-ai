from __future__ import annotations

import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    use_queue_ingest: bool = os.getenv("USE_QUEUE_INGEST", "false").lower() == "true"
    orchestration_engine: str = os.getenv("ORCHESTRATION_ENGINE", "custom").lower()


settings = Settings()
