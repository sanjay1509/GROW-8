"""OPPORTUNITY_CREATED -> tell contributors whose skills match the new opportunity."""

import logging
from collections.abc import Callable, Sequence

from grow8_common.events import OpportunityCreatedPayload
from grow8_common.notifications import Notifier
from grow8_common.queries import (
    ContributorMatch,
    find_matching_contributors,
    is_opportunity_open,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FindMatches = Callable[[Session, Sequence[str]], list[ContributorMatch]]
IsOpen = Callable[[Session, int], bool]


def handle_opportunity_created(
    payload: OpportunityCreatedPayload,
    *,
    session: Session,
    notifier: Notifier,
    find_matches: FindMatches = find_matching_contributors,
    is_open: IsOpen = is_opportunity_open,
) -> list[ContributorMatch]:
    """Notify every matching contributor once and return who was notified.

    The only writes are the notifier's, and it stores one notification per user per
    event, so handling the same event twice (at-least-once delivery) adds nothing.
    The caller commits.
    """
    if not is_open(session, payload.opportunity_id):
        logger.info(
            "opportunity_id=%s is no longer open; skipping notifications",
            payload.opportunity_id,
        )
        return []

    matches = find_matches(session, payload.skill_codes)
    deadline = payload.application_deadline.strftime("%Y-%m-%d %H:%M UTC")
    for match in matches:
        skills = ", ".join(match.matched_skill_codes) or "open to everyone"
        notifier.notify(
            match.user_id,
            f"New opportunity: {payload.title}",
            f"Apply by {deadline}. Your matching skills: {skills}.",
            opportunity_id=payload.opportunity_id,
        )

    logger.info(
        "opportunity_id=%s skill_codes=%s notified %d contributor(s): %s",
        payload.opportunity_id,
        payload.skill_codes,
        len(matches),
        [m.user_id for m in matches],
    )
    return matches
