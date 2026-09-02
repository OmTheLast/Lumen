import time
from threading import Thread

from lumen.agent.schemas import Action, Risk
from lumen.agent.safety import SafetyBroker
from lumen.approvals import ApprovalBroker


def test_approval_broker_resolves_pending_request():
    broker = ApprovalBroker()
    result: list[bool] = []

    thread = Thread(
        target=lambda: result.append(
            broker.request(
                Action("run_shell", {"command": "echo hi"}, "testing"),
                risk=Risk.HIGH,
                risk_reason="Can run commands.",
            )
        )
    )
    thread.start()

    deadline = time.time() + 1
    approvals = []
    while time.time() < deadline:
        approvals = broker.snapshot()["approvals"]
        if approvals:
            break
        time.sleep(0.01)
    pending = approvals[0]
    assert pending["status"] == "pending"
    assert broker.resolve(pending["id"], approved=True) is not None

    thread.join(timeout=1)
    assert result == [True]
    assert broker.snapshot()["approvals"][0]["status"] == "approved"


def test_safety_broker_rejects_risky_action_without_interaction():
    broker = SafetyBroker(interactive=False)
    action = Action("run_shell", {"command": "echo hi"})
    decision = broker.assess(action)

    assert broker.confirm(action, decision) is False
