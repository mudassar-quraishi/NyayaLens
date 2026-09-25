"""
Provider-agnostic LLM wrapper for NyayaLens.

Supports Gemini and Anthropic. Reads model from LLM_MODEL env var.
Includes: retry, JSON repair, token/latency logging, DEMO_MODE fixture serving.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger("nyayalens.llm")

T = TypeVar("T", bound=BaseModel)

# Global concurrency semaphore (set in init)
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().max_concurrent_llm_calls)
    return _semaphore


# ── JSON Repair ────────────────────────────────────────────────────

def repair_json(text: str) -> str:
    """Attempt to extract and repair JSON from LLM output."""
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text.strip())

    # Try to find JSON object or array
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching end, counting nesting
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    return text  # Return as-is; let JSON parser report the error


# ── Fixture Handling (DEMO_MODE) ──────────────────────────────────

def _fixture_key(content_hash: str, prompt_name: str) -> str:
    """Build a fixture cache key from document hash and prompt name."""
    return f"{content_hash}__{prompt_name}"


def _load_fixture(content_hash: str, prompt_name: str) -> dict | None:
    """Load a pre-computed fixture if it exists and DEMO_MODE is on."""
    settings = get_settings()
    if not settings.demo_mode:
        return None

    fixtures_dir = settings.fixtures_dir
    key = _fixture_key(content_hash, prompt_name)
    path = fixtures_dir / f"{key}.json"
    if path.exists():
        logger.info("DEMO_MODE: serving fixture %s", key)
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_fixture(content_hash: str, prompt_name: str, data: dict) -> None:
    """Save a computed result as a fixture for future DEMO_MODE use."""
    settings = get_settings()
    fixtures_dir = settings.fixtures_dir
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    key = _fixture_key(content_hash, prompt_name)
    path = fixtures_dir / f"{key}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved fixture: %s", key)


def is_sample_document(content_hash: str) -> bool:
    """Check if a document hash matches one of the bundled samples."""
    settings = get_settings()
    sample_hashes_path = settings.fixtures_dir / "sample_hashes.json"
    if sample_hashes_path.exists():
        hashes = json.loads(sample_hashes_path.read_text(encoding="utf-8"))
        return content_hash in hashes
    return False


def compute_content_hash(text: str) -> str:
    """SHA-256 hash of normalized text content."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


# ── Gemini Client ─────────────────────────────────────────────────

async def _call_gemini(system: str, user: str, model: str) -> str:
    """Call Google Gemini API."""
    from google import genai
    from google.genai import types

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text


# ── Anthropic Client ──────────────────────────────────────────────

async def _call_anthropic(system: str, user: str, model: str) -> str:
    """Call Anthropic Claude API."""
    import anthropic

    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ── Groq Client ───────────────────────────────────────────────────

async def _call_groq(system: str, user: str, model: str, json_mode: bool = False) -> str:
    """Call Groq API using AsyncGroq client."""
    from groq import AsyncGroq

    settings = get_settings()
    client = AsyncGroq(api_key=settings.groq_api_key)

    groq_model = model
    # Use high-quality default if a Gemini/Anthropic model string was passed
    if not groq_model or "gemini" in groq_model.lower() or "claude" in groq_model.lower():
        groq_model = "llama-3.3-70b-versatile"

    kwargs: dict[str, Any] = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


# ── Core Interface ────────────────────────────────────────────────

class LLMMetrics:
    """Simple token and latency logger."""

    def __init__(self):
        self.calls: list[dict] = []

    def log(self, prompt_name: str, latency_ms: float, input_len: int, output_len: int):
        entry = {
            "prompt": prompt_name,
            "latency_ms": round(latency_ms, 1),
            "input_chars": input_len,
            "output_chars": output_len,
            "timestamp": time.time(),
        }
        self.calls.append(entry)
        logger.info(
            "LLM call: %s — %.0fms, %d→%d chars",
            prompt_name, latency_ms, input_len, output_len,
        )

    def summary(self) -> dict:
        if not self.calls:
            return {"total_calls": 0}
        latencies = [c["latency_ms"] for c in self.calls]
        latencies.sort()
        return {
            "total_calls": len(self.calls),
            "p50_latency_ms": latencies[len(latencies) // 2],
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
            "total_input_chars": sum(c["input_chars"] for c in self.calls),
            "total_output_chars": sum(c["output_chars"] for c in self.calls),
        }


# Global metrics instance
metrics = LLMMetrics()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((json.JSONDecodeError, ValidationError, Exception)),
    reraise=True,
)
async def generate_json(
    schema: Type[T],
    system: str,
    user: str,
    prompt_name: str = "unknown",
    content_hash: str | None = None,
) -> T:
    """
    Call the LLM, parse and validate the JSON response against a Pydantic schema.

    Args:
        schema: Pydantic model class to validate against
        system: System prompt
        user: User prompt
        prompt_name: Name for logging and fixture keying
        content_hash: Document content hash for DEMO_MODE fixture lookup
    """
    # Check fixture cache first
    if content_hash:
        fixture = _load_fixture(content_hash, prompt_name)
        if fixture is not None:
            return schema.model_validate(fixture)

    settings = get_settings()
    model = settings.llm_model

    sem = _get_semaphore()
    async with sem:
        t0 = time.monotonic()

        if settings.llm_provider == "groq":
            raw = await _call_groq(system, user, model, json_mode=True)
        elif settings.llm_provider == "anthropic":
            raw = await _call_anthropic(system, user, model)
        else:
            raw = await _call_gemini(system, user, model)

        latency = (time.monotonic() - t0) * 1000
        metrics.log(prompt_name, latency, len(system) + len(user), len(raw))

    # Parse and validate
    repaired = repair_json(raw)
    data = json.loads(repaired)
    result = schema.model_validate(data)

    # Cache for future DEMO_MODE
    if content_hash:
        save_fixture(content_hash, prompt_name, data)

    return result


async def generate_text(
    system: str,
    user: str,
    prompt_name: str = "unknown",
) -> str:
    """Call the LLM and return raw text (no JSON parsing)."""
    settings = get_settings()
    model = settings.llm_model

    sem = _get_semaphore()
    async with sem:
        t0 = time.monotonic()

        if settings.llm_provider == "groq":
            raw = await _call_groq(system, user, model, json_mode=False)
        elif settings.llm_provider == "anthropic":
            raw = await _call_anthropic(system, user, model)
        else:
            raw = await _call_gemini(system, user, model)

        latency = (time.monotonic() - t0) * 1000
        metrics.log(prompt_name, latency, len(system) + len(user), len(raw))

    return raw


# ── Embedding ─────────────────────────────────────────────────────

_embedding_model = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        settings = get_settings()
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Loaded embedding model: %s", settings.embedding_model)
    return _embedding_model


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the multilingual sentence-transformers model."""
    model = _get_embedding_model()
    embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
    return embeddings.tolist()
