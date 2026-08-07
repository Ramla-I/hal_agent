"""Central LLM call layer: per-stage model lists, Groq key pool, smart retries.

`call_llm` is the single entry point the generator and analyzer use. It:
  * walks an ordered list of models (from config.STAGE_MODELS or an explicit list)
    and OVERFLOWS to the next model when one is persistently rate-limited
    (e.g. Groq TPM exhausted -> fall back to a low-cost OpenAI model);
  * routes each model to its provider (config.GROQ_MODELS -> the Groq key pool,
    everything else -> OpenAI) and ROUND-ROBINS the Groq key pool so parallel
    workers spread load across keys/accounts;
  * retries transient errors honoring the server's 429 retry hint (the
    `retry-after` header or the "try again in Xs" body) instead of blind
    exponential backoff.
"""
from __future__ import annotations

import itertools
import logging
import random
import re
import threading
import time
from typing import Optional

import config
from utils.utils import get_model_string

logger = logging.getLogger(__name__)

# Thread-safe round-robin over the Groq key pool.
_rr_lock = threading.Lock()
_rr_counter = itertools.count()


def _next_groq_client():
    if not config.GROQ_CLIENTS:
        raise RuntimeError(
            "A Groq model was requested but no Groq keys are configured "
            "(set GROQ_API_KEY or GROQ_API_KEYS)."
        )
    with _rr_lock:
        i = next(_rr_counter)
    idx = i % len(config.GROQ_CLIENTS)
    return config.GROQ_CLIENTS[idx], idx


def _client_for_model(model: str):
    """Return (client, label) for a model based on config routing."""
    if model in config.GROQ_MODELS:
        client, idx = _next_groq_client()
        return client, f"groq[{idx}]"
    return config.client_openai, "openai"


def _retry_after_seconds(err: Exception) -> Optional[float]:
    """Extract the server's requested wait from a 429: the retry-after header,
    else the "try again in Xs" hint in the message body."""
    resp = getattr(err, "response", None)
    if resp is not None:
        headers = getattr(resp, "headers", None)
        if headers:
            val = headers.get("retry-after") or headers.get("Retry-After")
            if val:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass
    m = re.search(r"try again in ([0-9.]+)\s*s", str(err))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def call_llm(
    stage: Optional[str] = None,
    *,
    models: Optional[list[str]] = None,
    max_retries: int = 6,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    **kwargs,
):
    """Run a responses.create call across a stage's model list with retries.

    Provide either ``stage`` (looked up in config.STAGE_MODELS) or an explicit
    ``models`` list (takes precedence). Returns ``(response, used_model)``.
    Raises the last error if every model is exhausted.
    """
    from openai import (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )
    transient = (InternalServerError, RateLimitError, APIConnectionError, APITimeoutError)

    model_list = models if models is not None else (config.STAGE_MODELS.get(stage) if stage else None)
    if not model_list:
        raise ValueError(f"No models configured for stage={stage!r} / models={models!r}")

    last_error: Optional[Exception] = None
    for mi, model in enumerate(model_list):
        is_last_model = (mi == len(model_list) - 1)
        for attempt in range(max_retries):
            client, label = _client_for_model(model)
            try:
                response = client.responses.create(model=get_model_string(model), **kwargs)
                if mi > 0:
                    logger.error("Stage %s: succeeded on overflow model %s (%s)", stage, model, label)
                return response, model
            except transient as e:
                last_error = e
                if attempt == max_retries - 1:
                    # Exhausted this model; overflow to the next if any.
                    nxt = "next model" if not is_last_model else "no more models"
                    logger.error(
                        "Stage %s model %s (%s): %s exhausted %d retries -> %s",
                        stage, model, label, type(e).__name__, max_retries, nxt,
                    )
                    break
                hinted = _retry_after_seconds(e)
                delay = hinted if hinted is not None else base_delay * (2 ** attempt)
                delay = min(delay, max_delay)
                delay += random.uniform(0, min(1.0, delay * 0.25))  # jitter
                logger.warning(
                    "Stage %s model %s (%s): %s; retry %d/%d in %.1fs%s",
                    stage, model, label, type(e).__name__, attempt + 1, max_retries, delay,
                    " (server-hinted)" if hinted is not None else "",
                )
                time.sleep(delay)
    raise last_error
