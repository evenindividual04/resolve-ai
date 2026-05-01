from evals.run_eval import run_eval_suite


def test_red_team_eval_executes() -> None:
    result = run_eval_suite()
    assert result["cases"] >= 3
    assert any(o["action"] in {"clarify", "escalate"} for o in result["outcomes"])
