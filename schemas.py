"""Request validation models."""
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

import config

Tone = Literal["professional", "casual", "concise"]


class ChatRequest(BaseModel):
    message: str
    tone: Tone = "professional"
    conversation_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        if len(value) > config.MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message is too long (max {config.MAX_MESSAGE_LENGTH} characters).")
        return value
