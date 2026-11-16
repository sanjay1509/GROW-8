from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDateTime


class ResumeRead(BaseModel):
    """A contributor's resume metadata. The file itself is downloaded separately."""

    model_config = ConfigDict(from_attributes=True)

    file_name: str
    content_type: str
    size_bytes: int
    uploaded_at: UtcDateTime
