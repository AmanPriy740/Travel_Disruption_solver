"""
Pydantic schemas for the ingestion layer.
No LLM calls happen anywhere in this module, on purpose.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DisruptionStatus(str, Enum):
    cancelled = "cancelled"
    delayed = "delayed"
    missed_connection = "missed_connection"


class DisruptionEvent(BaseModel):
    """Shape of an inbound flight-status webhook payload."""

    flight_id: str = Field(..., min_length=1)
    status: DisruptionStatus
    pax_id: str = Field(..., min_length=1)
    original_itinerary: str = Field(
        ..., description="Itinerary/booking reference this disruption applies to"
    )
    delay_minutes: Optional[int] = Field(
        default=None, ge=0, description="Required when status == 'delayed'"
    )

    @field_validator("delay_minutes")
    @classmethod
    def delay_required_when_delayed(cls, v, info):
        status = info.data.get("status")
        if status == DisruptionStatus.delayed and v is None:
            raise ValueError("delay_minutes is required when status is 'delayed'")
        return v


class IngestResult(BaseModel):
    accepted: bool
    event_id: Optional[str] = None
    reason: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)
