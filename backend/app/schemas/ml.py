"""Pydantic schemas: ml_predictions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


class MLPredictionBase(BaseModel):
    boiler_id: int
    timestamp: datetime
    probability: Decimal = Field(ge=0, le=1)
    predicted_failure_type: Optional[str] = Field(default=None, max_length=100)
    horizon_minutes: int = Field(gt=0)
    triggered_alert: bool = False
    actual_outcome: Optional[str] = Field(default=None, max_length=30)


class MLPredictionCreate(MLPredictionBase):
    pass


class MLPredictionUpdate(BaseModel):
    triggered_alert: Optional[bool] = None
    actual_outcome: Optional[str] = Field(default=None, max_length=30)


class MLPredictionResponse(MLPredictionBase, OrmModel):
    id: int
