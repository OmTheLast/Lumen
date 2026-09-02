"""In-app approval queue for risky Lumen actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Condition
from typing import Any
from uuid import uuid4

from lumen.agent.schemas import Action, Risk


@dataclass
class ApprovalRequest:
    id: str
    tool: str
    args: dict[str, Any]
    reason: str
    risk: str
    risk_reason: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: _now())
    resolved_at: str = ""


class ApprovalBroker:
    def __init__(self) -> None:
        self._condition = Condition()
        self._requests: dict[str, ApprovalRequest] = {}

    def request(
        self,
        action: Action,
        *,
        risk: Risk,
        risk_reason: str,
        timeout: float = 300.0,
    ) -> bool:
        approval = ApprovalRequest(
            id=uuid4().hex[:10],
            tool=action.tool,
            args=dict(action.args),
            reason=action.reason or "No reason provided.",
            risk=risk.value,
            risk_reason=risk_reason,
        )
        with self._condition:
            self._requests[approval.id] = approval
            self._condition.notify_all()
            self._condition.wait_for(lambda: approval.status != "pending", timeout=timeout)
            if approval.status == "pending":
                approval.status = "expired"
                approval.resolved_at = _now()
                self._condition.notify_all()
            return approval.status == "approved"

    def resolve(self, approval_id: str, approved: bool) -> ApprovalRequest | None:
        with self._condition:
            approval = self._requests.get(approval_id)
            if approval is None or approval.status != "pending":
                return None
            approval.status = "approved" if approved else "rejected"
            approval.resolved_at = _now()
            self._condition.notify_all()
            return _copy_approval(approval)

    def snapshot(self, limit: int = 24) -> dict[str, list[dict[str, Any]]]:
        with self._condition:
            requests = sorted(self._requests.values(), key=lambda item: item.created_at, reverse=True)
            return {"approvals": [asdict(item) for item in requests[:limit]]}

    def pending_count(self) -> int:
        with self._condition:
            return sum(1 for item in self._requests.values() if item.status == "pending")


def _copy_approval(approval: ApprovalRequest) -> ApprovalRequest:
    return ApprovalRequest(**asdict(approval))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
