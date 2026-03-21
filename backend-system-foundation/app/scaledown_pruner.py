"""
Scaledown context pruning accelerator.

Position in pipeline:
  ML Severity Engine → Scaledown (Pruning) → LLM Reasoner

Constraints:
  - Deterministic output
  - No semantic distortion
  - Latency overhead <20ms target (network permitting)
  - 70-90% token reduction
"""

import os
import logging
import httpx
from typing import Optional

# Load .env from backend-system-foundation directory
try:
    from dotenv import load_dotenv as _load_dotenv
    import pathlib as _pl
    _env_file = _pl.Path(__file__).parent.parent / ".env"
    if _env_file.exists():
        _load_dotenv(_env_file)
except ImportError:
    pass

logger = logging.getLogger(__name__)

SCALEDOWN_API_URL = "https://api.scaledown.xyz/compress/raw/"
SCALEDOWN_API_KEY = os.getenv("SCALEDOWN_API_KEY", "")
SCALEDOWN_TIMEOUT = 4.0  # seconds — allow up to 4s for compression API

# If env var not set, try reading directly from .env file
if not SCALEDOWN_API_KEY:
    try:
        import pathlib as _pl
        _env_path = _pl.Path(__file__).parent.parent / ".env"
        for _line in _env_path.read_text().splitlines():
            if _line.startswith("SCALEDOWN_API_KEY="):
                SCALEDOWN_API_KEY = _line.split("=", 1)[1].strip()
                break
    except Exception:
        pass


class ScaledownPruner:
    """
    Lightweight wrapper around the Scaledown compression API.

    Accepts raw patient context (notes, history, extracted features)
    and returns a compressed version retaining clinically relevant entities.
    """

    def __init__(self, api_key: Optional[str] = None, rate: str = "auto"):
        self.api_key = api_key or SCALEDOWN_API_KEY
        self.rate = rate
        self._enabled = bool(self.api_key)
        if not self._enabled:
            logger.warning("ScaledownPruner: no API key set — pruning disabled, passthrough mode")

    async def prune(
        self,
        context: str,
        prompt: str = "Summarize clinically relevant triage information.",
    ) -> dict:
        """
        Compress patient context via Scaledown API.

        Args:
            context: Raw patient notes / history / extracted features
            prompt:  The downstream query (helps Scaledown know what to keep)

        Returns:
            {
                "compressed_context": str,   # pruned text to pass to LLM
                "original_tokens": int,
                "compressed_tokens": int,
                "compression_ratio": float,  # 0-1, higher = more compressed
                "pruning_applied": bool,
                "error": str | None
            }
        """
        if not self._enabled or not context.strip():
            return self._passthrough(context)

        try:
            async with httpx.AsyncClient(timeout=SCALEDOWN_TIMEOUT) as client:
                response = await client.post(
                    SCALEDOWN_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "context": context,
                        "prompt": prompt,
                        "scaledown": {"rate": self.rate},
                    },
                )
                response.raise_for_status()
                data = response.json()

            if not data.get("successful", False):
                logger.warning("Scaledown returned unsuccessful response — passthrough")
                return self._passthrough(context, error="Scaledown unsuccessful")

            # Response structure: data.results.compressed_prompt
            results = data.get("results", data)
            original = results.get("original_prompt_tokens", len(context.split()))
            compressed_count = results.get("compressed_prompt_tokens", original)
            compressed_text = results.get("compressed_prompt", context)
            ratio = round(1 - (compressed_count / original), 3) if original > 0 else 0.0

            logger.info(
                f"Scaledown pruning: {original} → {compressed_count} tokens "
                f"({ratio:.1%} reduction)"
            )

            return {
                "compressed_context": compressed_text,
                "original_tokens": original,
                "compressed_tokens": compressed_count,
                "compression_ratio": ratio,
                "pruning_applied": True,
                "error": None,
            }

        except httpx.TimeoutException:
            logger.warning("Scaledown timeout — passthrough mode")
            return self._passthrough(context, error="timeout")
        except Exception as e:
            logger.warning(f"Scaledown error: {e} — passthrough mode")
            return self._passthrough(context, error=str(e))

    @staticmethod
    def _passthrough(context: str, error: Optional[str] = None) -> dict:
        token_count = len(context.split())
        return {
            "compressed_context": context,
            "original_tokens": token_count,
            "compressed_tokens": token_count,
            "compression_ratio": 0.0,
            "pruning_applied": False,
            "error": error,
        }


# Singleton — reused across requests
_pruner: Optional[ScaledownPruner] = None


def get_pruner() -> ScaledownPruner:
    global _pruner
    if _pruner is None:
        _pruner = ScaledownPruner()
    return _pruner
