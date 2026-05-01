from __future__ import annotations

import chaos.fault_injection as fi
from chaos.fault_injection import FaultConfig, FaultInjector


def test_fault_injector_zero_rates() -> None:
    f = FaultInjector(FaultConfig(llm_timeout_rate=0.0, db_failure_rate=0.0, delayed_webhook_rate=0.0))
    assert f.should_timeout_llm() is False
    assert f.should_fail_db() is False
    assert f.should_delay_webhook() is False


def test_fault_injector_full_rates() -> None:
    f = FaultInjector(FaultConfig(llm_timeout_rate=1.0, db_failure_rate=1.0, delayed_webhook_rate=1.0))
    assert f.should_timeout_llm() is True
    assert f.should_fail_db() is True
    assert f.should_delay_webhook() is True
