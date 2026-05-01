"""Integration tests for multi-turn simulation with BorrowerSimulator."""
from __future__ import annotations

import pytest

from domain.borrower import BorrowerProfile, RiskBand
from domain.models import WorkflowState, WorkflowStatus
from evals.borrower_simulator import BorrowerSimulator
from agents.profile_loader import ProfileLoader


sim = BorrowerSimulator()
loader = ProfileLoader()


def _state(outstanding: float = 10000.0) -> WorkflowState:
    return WorkflowState(
        workflow_id="sim-test-wf",
        user_id="sim-user",
        outstanding_amount=outstanding,
    )


def _profile(persona: str) -> BorrowerProfile:
    return loader.load_persona(f"user-{persona}", persona, 10000.0)


def test_cooperative_persona_generates_payment_message():
    profile = _profile("cooperative")
    state = _state()
    response = sim.generate_response("cooperative", state, profile, turn=1)
    assert response is not None
    assert len(response) > 5


def test_ghost_persona_returns_none():
    profile = _profile("ghost")
    state = _state()
    response = sim.generate_response("ghost", state, profile, turn=1)
    assert response is None


def test_adversarial_persona_contains_abusive_content():
    profile = _profile("adversarial")
    state = _state()
    response = sim.generate_response("adversarial", state, profile, turn=1)
    assert response is not None
    # Should contain adversarial signals
    lower = response.lower()
    assert any(kw in lower for kw in ["harassment", "complaint", "idiot", "illegal", "sue"])


def test_distressed_persona_mentions_hardship():
    profile = _profile("distressed")
    state = _state()
    response = sim.generate_response("distressed", state, profile, turn=1)
    assert response is not None
    lower = response.lower()
    assert any(kw in lower for kw in ["hardship", "job", "financial", "hardship"])


def test_negotiator_anchors_low_on_turn_1():
    profile = _profile("negotiator")
    state = _state(outstanding=10000.0)
    response = sim.generate_response("negotiator", state, profile, turn=1)
    assert response is not None
    # Should mention an amount lower than outstanding
    import re
    amounts = [float(m) for m in re.findall(r"\d+", response) if float(m) > 1000]
    if amounts:
        assert min(amounts) < 10000.0


def test_liar_commits_on_turn_1():
    profile = _profile("liar")
    state = _state()
    response = sim.generate_response("liar", state, profile, turn=1)
    assert response is not None
    lower = response.lower()
    assert "pay" in lower


def test_unknown_persona_raises():
    profile = _profile("cooperative")
    state = _state()
    with pytest.raises(ValueError, match="Unknown persona"):
        sim.generate_response("unicorn", state, profile, turn=1)


def test_all_personas_produce_consistent_responses():
    """Smoke test: all personas produce a response or None (ghost) across 3 turns."""
    personas = ["cooperative", "negotiator", "ghost", "liar", "distressed", "adversarial"]
    for persona in personas:
        profile = _profile(persona)
        state = _state()
        for turn in range(1, 4):
            response = sim.generate_response(persona, state, profile, turn)
            if persona == "ghost":
                assert response is None
            else:
                assert isinstance(response, str)
