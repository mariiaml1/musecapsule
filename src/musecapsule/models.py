
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True) 

    goal: str = Field(min_length=1)
    constraints: list[str]  = Field(default_factory=list)

class Message(BaseModel):
    id:UUID = Field(default_factory=uuid4)
    role: Literal['user', 'assistant']
    text: str = Field(min_length=1)

    @field_validator("text", mode="after")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message text must not be blank.")
        return value

class EvidenceRef(BaseModel):
    message_id: UUID
    quote: str = Field(min_length=1)

    @field_validator("quote", mode="after")
    @classmethod
    def reject_blank_quote(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Evidence quote must not be blank.")
        return value
