"""
Gemini LLM Reasoning Layer.

Position in pipeline:
  ML Severity Engine → Scaledown (Context Pruning) → Gemini (Reasoning) → Final Decision

Role:
  - Takes ML outputs (severity, probabilities) + Scaledown-compressed context
  - Produces structured clinical reasoning, severity justification, recommended actions
  - Strict JSON output — no free text, no hallucination beyond given data
  - Fail-safe: falls back to rule-based output if Gemini is unavailable
"""

import os
import json
import logging
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)

# Load API key from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite")

if not GEMINI_API_KEY:
    try:
        _env_path = pathlib.Path(__file__).parent.parent / ".env"
        for _line in _env_path.read_text().splitlines():
            if _line.startswith("GEMINI_API_KEY="):
                GEMINI_API_KEY = _line.split("=", 1)[1].strip()
            if _line.startswith("GEMINI_MODEL="):
                _val = _line.split("=", 1)[1].strip()
                if _val:
                    GEMINI_MODEL = _val
    except Exception:
        pass

# Ensure model name has models/ prefix
if GEMINI_MODEL and not GEMINI_MODEL.startswith("models/"):
    GEMINI_MODEL = f"models/{GEMINI_MODEL}"

# Override to known-working model
GEMINI_MODEL = "models/gemini-2.5-flash-lite"

_client = None

def _get_client():
    global _client
    if _client is None and GEMINI_API_KEY:
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.warning(f"Gemini client init failed: {e}")
    return _client


# ── Rule-based fallback recommendations (used when Gemini unavailable) ────────
_FALLBACK_REASONING = {
    "CRITICAL": {
        "severity_justification": "Vital signs indicate life-threatening condition requiring immediate intervention.",
        "recommended_actions": [
            "Establish IV access immediately",
            "Administer supplemental oxygen",
            "Prepare crash cart / intubation equipment",
            "Notify attending physician STAT",
            "Continuous cardiac monitoring",
        ],
        "reasoning_trace": [
            "Critical vital sign thresholds exceeded",
            "Immediate intervention required to prevent deterioration",
            "Safety override applied — escalated to CRITICAL",
        ],
        "clinical_priority": "IMMEDIATE",
        "estimated_wait_minutes": 0,
    },
    "HIGH": {
        "severity_justification": "Significant abnormalities in vital signs or symptoms indicating urgent care needed.",
        "recommended_actions": [
            "Administer pain management protocol",
            "Order STAT imaging (X-ray / CT)",
            "Notify attending physician within 15 minutes",
            "Establish IV access",
        ],
        "reasoning_trace": [
            "Multiple abnormal vital signs detected",
            "Symptom pattern consistent with urgent condition",
            "Physician notification required within 15 minutes",
        ],
        "clinical_priority": "URGENT",
        "estimated_wait_minutes": 15,
    },
    "MEDIUM": {
        "severity_justification": "Moderate abnormalities present. Patient stable but requires timely evaluation.",
        "recommended_actions": [
            "Administer antipyretics if febrile",
            "Obtain blood panel and urinalysis",
            "Monitor vitals every 30 minutes",
            "Schedule physician evaluation within 1 hour",
        ],
        "reasoning_trace": [
            "Vital signs show moderate deviation from normal",
            "Symptoms suggest non-life-threatening but significant condition",
            "Standard monitoring protocol initiated",
        ],
        "clinical_priority": "SEMI_URGENT",
        "estimated_wait_minutes": 60,
    },
    "LOW": {
        "severity_justification": "Vital signs within acceptable range. Condition appears non-urgent.",
        "recommended_actions": [
            "Document vitals and chief complaint",
            "Schedule non-urgent physician evaluation",
            "Provide comfort measures",
            "Reassess if symptoms worsen",
        ],
        "reasoning_trace": [
            "All vital signs within normal limits",
            "Symptoms consistent with non-urgent condition",
            "Standard intake protocol appropriate",
        ],
        "clinical_priority": "NON_URGENT",
        "estimated_wait_minutes": 120,
    },
}


def _build_prompt(
    compressed_context: str,
    risk_tier: str,
    confidence: float,
    calibrated_probability: float,
    age: int,
    symptoms: list,
) -> str:
    """Build a deterministic, guardrailed prompt for Gemini."""
    return f"""You are a clinical triage reasoning assistant. You receive structured patient data and ML model outputs. Your job is to produce a structured clinical reasoning response in strict JSON format.

PATIENT CONTEXT (compressed by Scaledown):
{compressed_context}

ML MODEL OUTPUT:
- Risk Tier: {risk_tier}
- Confidence: {round(confidence * 100, 1)}%
- Calibrated Probability: {round(calibrated_probability * 100, 1)}%
- Patient Age: {age}
- Reported Symptoms: {', '.join(symptoms) if symptoms else 'none reported'}

INSTRUCTIONS:
1. You MUST accept the ML risk tier as ground truth — do NOT change it
2. Provide clinical reasoning that JUSTIFIES the ML decision
3. Recommend actions appropriate for {risk_tier} severity
4. Base reasoning ONLY on the data provided — no assumptions
5. Output MUST be valid JSON matching the schema below exactly

OUTPUT SCHEMA (respond with ONLY this JSON, no other text):
{{
  "severity_justification": "1-2 sentence clinical explanation of why this severity tier is appropriate",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "reasoning_trace": ["key factor 1", "key factor 2", "key factor 3"],
  "clinical_priority": "IMMEDIATE|URGENT|SEMI_URGENT|NON_URGENT",
  "estimated_wait_minutes": <integer>,
  "gemini_reasoning": true
}}"""


async def reason(
    compressed_context: str,
    risk_tier: str,
    confidence: float,
    calibrated_probability: float,
    age: int,
    symptoms: list,
) -> dict:
    """
    Call Gemini to produce structured clinical reasoning.
    Falls back to rule-based output if Gemini is unavailable.

    Returns dict with:
      severity_justification, recommended_actions, reasoning_trace,
      clinical_priority, estimated_wait_minutes, gemini_reasoning (bool)
    """
    tier = risk_tier.upper()
    fallback = dict(_FALLBACK_REASONING.get(tier, _FALLBACK_REASONING["MEDIUM"]))
    fallback["gemini_reasoning"] = False

    client = _get_client()
    if client is None:
        logger.warning("Gemini client unavailable — using rule-based fallback")
        return fallback

    prompt = _build_prompt(
        compressed_context=compressed_context,
        risk_tier=tier,
        confidence=confidence,
        calibrated_probability=calibrated_probability,
        age=age,
        symptoms=symptoms,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        # Validate required fields
        required = ["severity_justification", "recommended_actions", "reasoning_trace",
                    "clinical_priority", "estimated_wait_minutes"]
        for field in required:
            if field not in result:
                raise ValueError(f"Missing field: {field}")

        result["gemini_reasoning"] = True
        logger.info(f"Gemini reasoning OK for {tier} patient")
        return result

    except Exception as e:
        logger.warning(f"Gemini reasoning failed: {e} — using fallback")
        return fallback


# Singleton check
def is_available() -> bool:
    return bool(GEMINI_API_KEY) and _get_client() is not None
