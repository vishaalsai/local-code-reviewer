import time
import httpx
import json
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = (
    "You are a code review assistant. You ALWAYS respond with ONLY valid JSON. "
    "Never include markdown, code fences, or any explanation outside the JSON object."
)

STRICT_RETRY_SUFFIX = (
    "\n\nCRITICAL: Your previous response was not valid JSON. "
    "You must respond with ONLY a valid JSON object. "
    "No markdown. No code fences. No explanation. Raw JSON only."
)


@dataclass
class OllamaResult:
    raw_text: str
    model: str
    tokens_per_second: float
    time_to_first_token_ms: float
    total_latency_ms: float


def load_prompt_template() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "code_review.txt")
    with open(prompt_path, "r") as f:
        return f.read()


def build_prompt(code: str, language: str, filename: str | None, strict: bool = False) -> str:
    template = load_prompt_template()
    file_info = f" (file: {filename})" if filename else ""
    prompt = template.format(language=language, file_info=file_info, code=code)
    if strict:
        prompt += STRICT_RETRY_SUFFIX
    return prompt


def _call_ollama(prompt: str, temperature: float = 0.0) -> OllamaResult:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "options": {
            "temperature": temperature,
        },
    }

    full_response: list[str] = []
    time_to_first_token_ms = 0.0
    first_token_received = False
    start_time = time.perf_counter()
    eval_count = 0
    eval_duration_ns = 0

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)

                if not first_token_received and chunk.get("response"):
                    time_to_first_token_ms = (time.perf_counter() - start_time) * 1000
                    first_token_received = True

                if chunk.get("response"):
                    full_response.append(chunk["response"])

                if chunk.get("done"):
                    eval_count = chunk.get("eval_count", 0)
                    eval_duration_ns = chunk.get("eval_duration", 0)
                    break

    total_latency_ms = (time.perf_counter() - start_time) * 1000
    tokens_per_second = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0

    return OllamaResult(
        raw_text="".join(full_response),
        model=OLLAMA_MODEL,
        tokens_per_second=round(tokens_per_second, 2),
        time_to_first_token_ms=round(time_to_first_token_ms, 2),
        total_latency_ms=round(total_latency_ms, 2),
    )


def extract_json(text: str) -> str:
    """Strip markdown fences and whitespace, then return the first JSON object found."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences the model may emit despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Find the outermost { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def review_code(
    code: str,
    language: str = "python",
    filename: str | None = None,
    temperature: float = 0.0,
) -> OllamaResult:
    prompt = build_prompt(code, language, filename, strict=False)
    return _call_ollama(prompt, temperature=temperature)


def review_code_strict_retry(
    code: str,
    language: str = "python",
    filename: str | None = None,
    temperature: float = 0.0,
) -> OllamaResult:
    """Retry variant that appends the strict JSON-only instruction."""
    prompt = build_prompt(code, language, filename, strict=True)
    return _call_ollama(prompt, temperature=temperature)
