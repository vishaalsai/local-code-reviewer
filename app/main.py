import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import (
    CodeReviewRequest,
    CodeReviewResponse,
    CodeReviewError,
    CodeIssue,
    ReviewMetrics,
    Severity,
)
from app.ollama_client import review_code, review_code_strict_retry, extract_json
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Local Code Reviewer", version="2.0.0")


def _parse_review(raw_text: str) -> dict:
    """Extract and parse JSON from the model's raw text response."""
    cleaned = extract_json(raw_text)
    return json.loads(cleaned)


def _build_response(data: dict, result, attempt: int) -> CodeReviewResponse:
    return CodeReviewResponse(
        summary=data["summary"],
        issues=[CodeIssue(**issue) for issue in data.get("issues", [])],
        suggestions=data.get("suggestions", []),
        overall_severity=Severity(data["overall_severity"]),
        metrics=ReviewMetrics(
            tokens_per_second=result.tokens_per_second,
            time_to_first_token_ms=result.time_to_first_token_ms,
            total_latency_ms=result.total_latency_ms,
        ),
        model=result.model,
        attempt=attempt,
    )


@app.get("/")
def root():
    return {"status": "running", "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get("http://localhost:11434/api/tags")
            r.raise_for_status()
        return {"status": "ok", "ollama": "reachable"}
    except Exception:
        return {"status": "ok", "ollama": "unreachable - start Ollama first"}


@app.post("/review", response_model=CodeReviewResponse)
def review(request: CodeReviewRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="code field must not be empty")

    # --- Attempt 1 ---
    log.info("Attempt 1: sending code review request (temperature=%.1f)", request.temperature)
    try:
        result = review_code(
            code=request.code,
            language=request.language,
            filename=request.filename,
            temperature=request.temperature,
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Make sure it is running at http://localhost:11434",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    log.info("Attempt 1 raw response (first 200 chars): %s", result.raw_text[:200])

    try:
        data = _parse_review(result.raw_text)
        response = _build_response(data, result, attempt=1)
        log.info("Attempt 1 succeeded — overall_severity=%s, issues=%d", response.overall_severity, len(response.issues))
        return response
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log.warning("Attempt 1 failed validation: %s", e)

    # --- Attempt 2 (strict retry) ---
    log.info("Attempt 2: retrying with strict JSON-only prompt")
    try:
        result2 = review_code_strict_retry(
            code=request.code,
            language=request.language,
            filename=request.filename,
            temperature=0.0,  # force deterministic on retry
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry call failed: {e}")

    log.info("Attempt 2 raw response (first 200 chars): %s", result2.raw_text[:200])

    try:
        data2 = _parse_review(result2.raw_text)
        response2 = _build_response(data2, result2, attempt=2)
        log.info("Attempt 2 succeeded — overall_severity=%s, issues=%d", response2.overall_severity, len(response2.issues))
        return response2
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log.error("Attempt 2 also failed validation: %s", e)

    # --- Both attempts failed — return structured error ---
    error_payload = CodeReviewError(
        error="Model did not return valid JSON after 2 attempts.",
        raw_response=result2.raw_text,
        metrics=ReviewMetrics(
            tokens_per_second=result2.tokens_per_second,
            time_to_first_token_ms=result2.time_to_first_token_ms,
            total_latency_ms=result2.total_latency_ms,
        ),
        model=result2.model,
    )
    return JSONResponse(status_code=422, content=error_payload.model_dump())
