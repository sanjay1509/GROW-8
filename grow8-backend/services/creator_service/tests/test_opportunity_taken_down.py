"""OPPORTUNITY_TAKEN_DOWN in creator_service (ADR 0016): the owner is told once, with
the admin's reason, and never who reported."""

from dataclasses import dataclass

import pytest
from grow8_common.events import EventEnvelope, EventType, OpportunityTakenDownPayload

from app import main
from app.handlers.opportunity_taken_down import handle_opportunity_taken_down

PAYLOAD = OpportunityTakenDownPayload(
    opportunity_id=1,
    organization_id=1,
    title="Recipes",
    reason="The pay is not what was advertised.",
    reporter_user_ids=[5, 6],
)


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


def test_the_owner_is_told_why() -> None:
    notifier = RecordingNotifier()

    result = handle_opportunity_taken_down(
        PAYLOAD, session=None, notifier=notifier, find_owner=lambda s, org: 2
    )

    assert result == 2
    [sent] = notifier.sent
    assert (sent.user_id, sent.opportunity_id) == (2, 1)
    assert sent.title == "Opportunity taken down: Recipes"
    assert 'Reason: "The pay is not what was advertised."' in sent.message
    # The reporters stay anonymous.
    assert "5" not in sent.message and "6" not in sent.message


def test_no_active_owner_notifies_nobody() -> None:
    notifier = RecordingNotifier()
    assert (
        handle_opportunity_taken_down(
            PAYLOAD, session=None, notifier=notifier, find_owner=lambda s, org: None
        )
        is None
    )
    assert notifier.sent == []


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

    monkeypatch.setattr(main, "handle_opportunity_taken_down", fake_handler)

    main._on_opportunity_taken_down(
        EventEnvelope.build(PAYLOAD, EventType.OPPORTUNITY_TAKEN_DOWN, "req-1"), PAYLOAD
    )

    assert calls == ["handle", "commit", "close"]
    assert seen["notifier"]._type == "opportunity_taken_down"
