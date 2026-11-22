"""OPPORTUNITY_TAKEN_DOWN and REPORT_DISMISSED in contributor_service (ADR 0016):
applicants and reporters are each told once; a dismissal reaches only its reporter."""

from dataclasses import dataclass

import pytest
from grow8_common.events import (
    EventEnvelope,
    EventType,
    OpportunityTakenDownPayload,
    ReportDismissedPayload,
)
from grow8_common.models import ApplicationStatus
from grow8_common.queries import ActiveApplicant

from app import main
from app.handlers.opportunity_taken_down import handle_opportunity_taken_down
from app.handlers.report_dismissed import handle_report_dismissed


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


def _taken_down(reporters: list[int]) -> OpportunityTakenDownPayload:
    return OpportunityTakenDownPayload(
        opportunity_id=1,
        organization_id=1,
        title="Recipes",
        reason="The pay is not what was advertised.",
        reporter_user_ids=reporters,
    )


APPLICANTS = [
    ActiveApplicant(5, ApplicationStatus.PENDING),
    ActiveApplicant(7, ApplicationStatus.ACCEPTED),
]


def test_applicants_and_reporters_are_each_told_once() -> None:
    notifier = RecordingNotifier()

    result = handle_opportunity_taken_down(
        _taken_down(reporters=[6, 7]),
        session=None,
        notifier=notifier,
        find_applicants=lambda s, o: APPLICANTS,
    )

    assert result == [5, 6, 7]
    by_user = {s.user_id: s for s in notifier.sent}
    assert len(notifier.sent) == 3  # Sam (7) applied and reported: one notification
    assert by_user[5].title == "Opportunity taken down: Recipes"
    assert "won't go ahead" in by_user[5].message
    for reporter in (6, 7):
        assert by_user[reporter].title == "Thanks for your report: Recipes"
    # The admin's reason was written for the creator, not for contributors.
    assert all("advertised" not in s.message for s in notifier.sent)


def test_nobody_to_tell() -> None:
    notifier = RecordingNotifier()
    assert (
        handle_opportunity_taken_down(
            _taken_down([]), session=None, notifier=notifier, find_applicants=lambda s, o: []
        )
        == []
    )
    assert notifier.sent == []


@pytest.mark.parametrize(
    ("reason", "ending"),
    [
        (None, "decided the opportunity can stay up."),
        ("The hours are listed.", 'Their note: "The hours are listed."'),
    ],
)
def test_a_dismissal_tells_only_its_reporter(reason: str | None, ending: str) -> None:
    notifier = RecordingNotifier()
    payload = ReportDismissedPayload(
        report_id=3,
        opportunity_id=1,
        opportunity_title="Recipes",
        reporter_user_id=6,
        reason=reason,
    )

    assert handle_report_dismissed(payload, session=None, notifier=notifier) == 6

    [sent] = notifier.sent
    assert (sent.user_id, sent.title) == (6, "Report reviewed: Recipes")
    assert sent.message.endswith(ending)


class FakeSession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("close")

    def commit(self) -> None:
        self.calls.append("commit")


@pytest.mark.parametrize(
    ("on_event", "handler_name", "payload", "event_type"),
    [
        (
            "_on_opportunity_taken_down",
            "handle_opportunity_taken_down",
            _taken_down([6]),
            EventType.OPPORTUNITY_TAKEN_DOWN,
        ),
        (
            "_on_report_dismissed",
            "handle_report_dismissed",
            ReportDismissedPayload(
                report_id=3,
                opportunity_id=1,
                opportunity_title="R",
                reporter_user_id=6,
                reason=None,
            ),
            EventType.REPORT_DISMISSED,
        ),
    ],
)
def test_wrappers_use_their_own_notification_type_then_commit(
    monkeypatch: pytest.MonkeyPatch, on_event, handler_name, payload, event_type
) -> None:
    calls: list[str] = []
    seen = {}
    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: FakeSession(calls))

    def fake_handler(payload, *, session, notifier):
        calls.append("handle")
        seen["notifier"] = notifier

    monkeypatch.setattr(main, handler_name, fake_handler)

    getattr(main, on_event)(EventEnvelope.build(payload, event_type, "req-1"), payload)

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == event_type.value.lower()
