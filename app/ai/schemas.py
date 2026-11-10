"""Small explicit output schemas limit both latency and unsupported claims."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Finding(Strict):
    summary: str = Field(max_length=500)
    log_ids: list[str] = Field(min_length=1,max_length=12)
    confidence: Literal['low','medium','high']

class SpecialistResult(Strict):
    findings: list[Finding] = Field(max_length=3)
    entities: list[str] = Field(max_length=24)

class TimelineEvent(Strict):
    explanation: str = Field(max_length=220)
    log_ids: list[str] = Field(min_length=1,max_length=12)

class LeadResult(Strict):
    events: list[TimelineEvent] = Field(min_length=1,max_length=8)
    summary: str = Field(max_length=400)
    summary_log_ids: list[str] = Field(min_length=1,max_length=32)

class ReviewResult(Strict):
    verdict: Literal['supports','uncertain','does_not_support']
    explanation: str = Field(max_length=700)
    log_ids: list[str] = Field(min_length=1,max_length=12)
    uncertainty: str = Field(max_length=400)
