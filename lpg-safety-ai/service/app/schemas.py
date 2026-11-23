from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal

class TagValue(BaseModel):
    value: float | bool | int
    ma: float | None = None
    quality: Literal["good", "suspect", "bad", "stale"] = "good"

class TagFrame(BaseModel):
    ts: str
    sim_speed: int
    tags: Dict[str, TagValue]

class Evidence(BaseModel):
    layer: str
    subject: str
    severity: float
    text: str
    data: dict = Field(default_factory=dict)

class Assessment(BaseModel):
    subject: str
    risk_score: int
    confidence: Literal["high", "medium", "low"]
    top_factors: List[str]
    leak_suspects: List[dict] = Field(default_factory=list)
    predictions: dict = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
