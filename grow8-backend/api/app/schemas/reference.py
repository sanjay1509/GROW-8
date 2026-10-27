from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str | None


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
