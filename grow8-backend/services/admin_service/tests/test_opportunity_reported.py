"""OPPORTUNITY_REPORTED handler: every active admin is told once (ADR 0016)."""

from dataclasses import dataclass

import pytest
from grow8_common.events import EventEnvelope, EventType, OpportunityReportedPayload

from app import main
from app.handlers.opportunity_reported import handle_opportunity_reported


@dataclass(frozen=True)
class Sent:
    user_id: int
    title: str
    message: str
    opportunity_id: int | None


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[Sent] = []

    def notify(
        self, user_id: int, title: str, message: str, *, opportunity_id: int | None = None
    ) -> None:
        self.sent.append(Sent(user_id, title, message, opportunity_id))


def _payload(
    reason: str = "unsafe_conditions", open_reports: int = 1
) -> OpportunityReportedPayload:
    return OpportunityReportedPayload(
        report_id=3,
        opportunity_id=1,
        opportunity_title="Recipes",
        reason=reason,
        open_reports=open_reports,
    )


def test_every_active_admin_is_told() -> None:
    notifier = RecordingNotifier()

    result = handle_opportunity_reported(
        _payload(), session=None, notifier=notifier, find_admins=lambda s: [1, 50]
    )

    assert result == [1, 50]
    assert [s.user_id for s in notifier.sent] == [1, 50]
    sent = notifier.sent[0]
    assert sent.title == "Opportunity reported: Recipes"
    assert sent.message == "A contributor reported it as unsafe conditions. It has 1 open report."
    assert sent.opportunity_id == 1


@pytest.mark.parametrize(
    ("reason", "words"),
    [
        ("misleading_terms", "misleading terms"),
        ("discriminatory", "discriminatory"),
        ("scam_or_spam", "a scam or spam"),
        ("other", "another reason"),
    ],
)
def test_each_reason_reads_naturally(reason: str, words: str) -> None:
    notifier = RecordingNotifier()
    handle_opportunity_reported(
        _payload(reason, 3), session=None, notifier=notifier, find_admins=lambda s: [1]
    )
    assert (
        notifier.sent[0].message == f"A contributor reported it as {words}. It has 3 open reports."
    )


class FakeSession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("close")

    def commit(self) -> None:
        self.calls.append("commit")


def test_wrapper_uses_its_own_notification_type_then_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    seen = {}
    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: FakeSession(calls))

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, "handle_opportunity_reported", fake_handler)
    payload = _payload()

    main._on_opportunity_reported(
        EventEnvelope.build(payload, EventType.OPPORTUNITY_REPORTED, "req-1"), payload
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == "opportunity_reported"
