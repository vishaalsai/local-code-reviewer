from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CodeIssue(BaseModel):
    line_number: int
    severity: Severity
    description: str


class ReviewMetrics(BaseModel):
    tokens_per_second: float
    time_to_first_token_ms: float
    total_latency_ms: float


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    filename: Optional[str] = None
    temperature: float = 0.0


class CodeReviewResponse(BaseModel):
    summary: str
    issues: list[CodeIssue]
    suggestions: list[str]
    overall_severity: Severity
    metrics: ReviewMetrics
    model: str
    attempt: int = 1


class CodeReviewError(BaseModel):
    error: str
    raw_response: str
    metrics: ReviewMetrics
    model: str
