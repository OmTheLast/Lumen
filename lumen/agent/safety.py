"""Confirmation policy for tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from lumen.approvals import ApprovalBroker
from lumen.agent.schemas import Action, Risk


@dataclass(frozen=True)
class SafetyDecision:
    risk: Risk
    needs_confirmation: bool
    reason: str


class SafetyBroker:
    high_risk_tools = {"run_shell", "write_file"}
    medium_risk_tools = {"screenshot"}

    def __init__(self, approval_broker: ApprovalBroker | None = None, *, interactive: bool = True) -> None:
        self.approval_broker = approval_broker
        self.interactive = interactive

    def assess(self, action: Action) -> SafetyDecision:
        if action.tool in self.high_risk_tools:
            return SafetyDecision(Risk.HIGH, True, "This action can change files or run arbitrary code.")
        if action.tool in self.medium_risk_tools:
            return SafetyDecision(Risk.MEDIUM, True, "This action may capture private screen contents.")
        return SafetyDecision(Risk.LOW, False, "This action is low risk.")

    def confirm(self, action: Action, decision: SafetyDecision) -> bool:
        if not decision.needs_confirmation:
            return True

        if self.approval_broker is not None:
            return self.approval_broker.request(
                action,
                risk=decision.risk,
                risk_reason=decision.reason,
            )

        if not self.interactive:
            return False

        print()
        print(f"Lumen wants to run `{action.tool}`")
        print(f"Reason: {action.reason or 'No reason provided.'}")
        print(f"Risk: {decision.risk.value} - {decision.reason}")
        print(f"Args: {action.args}")
        answer = input("Confirm? (y/n): ").strip().lower()
        return answer == "y"
