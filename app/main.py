from fastapi import FastAPI, HTTPException
from app.schemas import CodeReviewRequest, CodeReviewResponse
from app.ollama_client import review_code
import httpx

app = FastAPI(title="Local Code Reviewer", version="1.0.0")


@app.get("/")
def root():
    return {"status": "running", "docs": "/docs"}


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
    try:
        result = review_code(
            code=request.code,
            language=request.language,
            filename=request.filename,
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Make sure it is running at http://localhost:11434",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return CodeReviewResponse(
        review=result.review_text,
        model=result.model,
        tokens_per_second=result.tokens_per_second,
        time_to_first_token_ms=result.time_to_first_token_ms,
        total_latency_ms=result.total_latency_ms,
    )
