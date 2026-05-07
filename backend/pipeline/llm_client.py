from __future__ import annotations

import json
import time
from typing import Any


class LLMClientError(RuntimeError):
    pass


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _parse_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found")
    return json.loads(cleaned[start : end + 1])


class AnthropicJSONClient:
    def __init__(self, api_key: str, timeout_seconds: int = 30, max_attempts: int = 2) -> None:
        try:
            import anthropic
        except Exception as exc:  # pragma: no cover - dependency guard
            raise LLMClientError("anthropic package is not installed") from exc

        self._client = anthropic.Anthropic(api_key=api_key, timeout=float(timeout_seconds), max_retries=0)
        self._max_attempts = max_attempts

    def call_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 600,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.messages.create(
                    model=model,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw = _extract_text(response)
                return _parse_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt == self._max_attempts:
                    break
                time.sleep(0.6)
            except Exception as exc:
                last_exc = exc
                if attempt == self._max_attempts:
                    break
                time.sleep(0.6)
        raise LLMClientError(f"LLM call failed after retries: {last_exc}")

    def call_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.0,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.messages.create(
                    model=model,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return _extract_text(response)
            except Exception as exc:
                last_exc = exc
                if attempt == self._max_attempts:
                    break
                time.sleep(0.6)
        raise LLMClientError(f"LLM text call failed after retries: {last_exc}")
