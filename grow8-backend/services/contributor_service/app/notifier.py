"""How contributors are told about things.

For now a notification is one structured log line per contributor. Storing notifications
(an inbox the frontend can show) or sending email is a later change behind this same
interface; the handlers do not need to change.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def notify(self, user_id: int, message: str, **context: object) -> None: ...


class LogNotifier:
    def notify(self, user_id: int, message: str, **context: object) -> None:
        details = " ".join(f"{key}={value}" for key, value in sorted(context.items()))
        logger.info("NOTIFY user_id=%s %s | %s", user_id, details, message)
