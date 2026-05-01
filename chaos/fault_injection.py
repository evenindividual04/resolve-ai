from __future__ import annotations

from dataclasses import dataclass
from random import random


@dataclass
class FaultConfig:
    llm_timeout_rate: float = 0.0
    db_failure_rate: float = 0.0
    delayed_webhook_rate: float = 0.0


class FaultInjector:
    def __init__(self, cfg: FaultConfig | None = None) -> None:
        self.cfg = cfg or FaultConfig()

    def should_timeout_llm(self) -> bool:
        return random() < self.cfg.llm_timeout_rate

    def should_fail_db(self) -> bool:
        return random() < self.cfg.db_failure_rate

    def should_delay_webhook(self) -> bool:
        return random() < self.cfg.delayed_webhook_rate
