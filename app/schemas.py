from pydantic import BaseModel
from typing import Optional


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    filename: Optional[str] = None


class CodeReviewResponse(BaseModel):
    review: str
    model: str
    tokens_per_second: float
    time_to_first_token_ms: float
    total_latency_ms: float
