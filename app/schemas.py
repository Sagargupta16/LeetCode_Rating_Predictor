"""Pydantic request/response models."""

import re
from typing import List

from pydantic import BaseModel, field_validator

from app.config import CONTEST_NAME_RE


class Contest(BaseModel):
    name: str
    rank: int

    @field_validator("name")
    @classmethod
    def validate_contest_name(cls, v: str) -> str:
        if not CONTEST_NAME_RE.match(v):
            raise ValueError(
                "Contest name must match pattern: (weekly|biweekly)-contest-<number>"
            )
        return v

    @field_validator("rank")
    @classmethod
    def validate_rank(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Rank must be a positive integer")
        if v > 1_000_000:
            raise ValueError("Rank exceeds maximum allowed value")
        return v


class PredictionInput(BaseModel):
    username: str
    contests: List[Contest]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty")
        if len(v) > 50:
            raise ValueError("Username too long")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username contains invalid characters")
        return v


class PredictionOutput(BaseModel):
    contest_name: str
    prediction: float
    rating_before_contest: float
    rank: int
    total_participants: int
    rating_after_contest: float
    attended_contests_count: int
