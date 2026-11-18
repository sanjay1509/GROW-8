from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime

_CENTS = Decimal("0.01")

# Hours always carry two decimals, as in the DECIMAL(6, 2) column, so a submission reads
# the same ("6.50") whether it was just created or loaded again later.
Hours = Annotated[Decimal, AfterValidator(lambda hours: hours.quantize(_CENTS))]


class SubmissionCreate(BaseModel):
    """The form fields of a work submission; the files travel next to them."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=5_000, description="What you did")
    hours_claimed: Hours = Field(
        gt=0, le=Decimal("9999.99"), decimal_places=2, description="Hours you worked"
    )


class AttachmentRead(BaseModel):
    """An attachment's metadata. The file itself is downloaded separately."""

    model_config = ConfigDict(from_attributes=True)

    attachment_id: int
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_at: UtcDateTime


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: int
    application_id: int
    description: str
    hours_claimed: Hours
    submitted_at: UtcDateTime
    attachments: list[AttachmentRead]
