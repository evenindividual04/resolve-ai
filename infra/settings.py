from __future__ import annotations

import os


class Settings:
    supported_orchestration_engines = {"custom"}

    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    use_queue_ingest: bool = os.getenv("USE_QUEUE_INGEST", "false").lower() == "true"
    orchestration_engine: str = os.getenv("ORCHESTRATION_ENGINE", "custom").lower()
    queue_max_retries: int = int(os.getenv("QUEUE_MAX_RETRIES", "3"))
    queue_retry_backoff_seconds: float = float(os.getenv("QUEUE_RETRY_BACKOFF_SECONDS", "0.5"))
    llm_request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "12"))
    llm_request_max_retries: int = int(os.getenv("LLM_REQUEST_MAX_RETRIES", "3"))
    llm_min_request_interval_seconds: float = float(os.getenv("LLM_MIN_REQUEST_INTERVAL_SECONDS", "0"))

    def validate(self) -> None:
        if self.orchestration_engine not in self.supported_orchestration_engines:
            supported = ", ".join(sorted(self.supported_orchestration_engines))
            raise ValueError(
                f"Unsupported ORCHESTRATION_ENGINE={self.orchestration_engine!r}. Supported values: {supported}."
            )
        if self.queue_max_retries < 0:
            raise ValueError("QUEUE_MAX_RETRIES must be >= 0")
        if self.queue_retry_backoff_seconds < 0:
            raise ValueError("QUEUE_RETRY_BACKOFF_SECONDS must be >= 0")
        if self.llm_request_timeout_seconds <= 0:
            raise ValueError("LLM_REQUEST_TIMEOUT_SECONDS must be > 0")
        if self.llm_request_max_retries < 1:
            raise ValueError("LLM_REQUEST_MAX_RETRIES must be >= 1")
        if self.llm_min_request_interval_seconds < 0:
            raise ValueError("LLM_MIN_REQUEST_INTERVAL_SECONDS must be >= 0")


settings = Settings()
settings.validate()
