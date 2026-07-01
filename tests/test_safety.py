from lumen.agent.schemas import Action, Risk
from lumen.agent.safety import SafetyBroker


def test_open_app_is_low_risk():
    decision = SafetyBroker().assess(Action("open_app", {"app_name": "Safari"}))

    assert decision.risk == Risk.LOW
    assert decision.needs_confirmation is False


def test_shell_is_high_risk_and_confirmed():
    decision = SafetyBroker().assess(Action("run_shell", {"command": "rm -rf /tmp/nope"}))

    assert decision.risk == Risk.HIGH
    assert decision.needs_confirmation is True

