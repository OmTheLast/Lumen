"""Confirmation policy for tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from lumen.agent.schemas import Action, Risk


@dataclass(frozen=True)
class SafetyDecision:
    risk: Risk
    needs_confirmation: bool
    reason: str


class SafetyBroker:
    high_risk_tools = {"run_shell", "write_file"}
    medium_risk_tools = {"screenshot"}

    def assess(self, action: Action) -> SafetyDecision:
        if action.tool in self.high_risk_tools:
            return SafetyDecision(Risk.HIGH, True, "This action can change files or run arbitrary code.")
        if action.tool in self.medium_risk_tools:
            return SafetyDecision(Risk.MEDIUM, True, "This action may capture private screen contents.")
        return SafetyDecision(Risk.LOW, False, "This action is low risk.")

    def confirm(self, action: Action, decision: SafetyDecision) -> bool:
        if not decision.needs_confirmation:
            return True

        print()
        print(f"Lumen wants to run `{action.tool}`")
        print(f"Reason: {action.reason or 'No reason provided.'}")
        print(f"Risk: {decision.risk.value} - {decision.reason}")
        print(f"Args: {action.args}")
        answer = input("Confirm? (y/n): ").strip().lower()
        return answer == "y"

