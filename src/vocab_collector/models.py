"""Pydantic model describing the structured LLM response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class VocabResult(BaseModel):
    """One dictionary entry: the word, its Chinese meaning and discipline."""

    model_config = ConfigDict(extra="forbid")

    english: str
    chinese: str
    domain: str

    @field_validator("english", "chinese", "domain")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must be a non-empty string")
        return value.strip()