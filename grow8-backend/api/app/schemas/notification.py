from grow8_common.models import NotificationType
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.common import UtcDateTime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    notification_type: NotificationType
    title: str
    message: str
    opportunity_id: int | None
    read_at: UtcDateTime | None
    created_at: UtcDateTime

    @computed_field
    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class NotificationListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unread_only: bool = Field(False, description="Only notifications not yet read")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class UnreadCount(BaseModel):
    unread_count: int


class MarkAllReadResult(BaseModel):
    marked_read: int = Field(description="How many notifications were unread until now")
