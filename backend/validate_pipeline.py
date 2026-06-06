"""
End-to-end validation run across all 150 synthetic cases.
Validates: ML triage + Scaledown compression + reasoning layer (Gemini or fallback).
Reports: success rate, failure rate, per-stage validation.
"""

import json
import httpx
import asyncio
from datetime import datetime


REQUIRED_RESPONSE_FIELDS = [
    "risk_tier",
    "confidence",
    "inference_time_ms",
    "pruning",
    "compression_stats",
    "reasoning",
    "latency_breakdown",
]

REQUIRED_PRUNING_FIELDS = ["original_tokens", "compressed_tokens", "compression_ratio", "pruning_applied"]
REQUIRED_REASONING_FIELDS = ["severity_justification", "recommended_actions", "reasoning_trace", "clinical_priority"]
VALID_RISK_TIERS = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def validate_response(data: dict) -> list[str]:
    """Return list of validation errors. Empty = pass."""
    errors = []

    # Top-level fields
    for field in REQUIRED_RESPONSE_FIELDS:
        if field not in data:
            errors.append(f"Missing field: {field}")

    # Risk tier valid
    tier = data.get("risk_tier", "")
    if tier not in VALID_RISK_TIERS:
        errors.append(f"Invalid risk_tier: {tier!r}")

    # Confidence in range
    conf = data.get("confidence", -1)
    if not (0.0 <= conf <= 1.0):
        errors.append(f"Confidence out of range: {conf}")

    # Pruning fields
    pruning = data.get("pruning", {})
    for field in REQUIRED_PRUNING_FIELDS:
        if field not in pruning:
            errors.append(f"Missing pruning.{field}")

    # Compression stats
    cs = data.get("compression_stats", {})
    if "original_tokens" not in cs or "compressed_tokens" not in cs or "reduction_percent" not in cs:
        errors.append("Incomplete compression_stats")
    elif cs.get("original_tokens", 0) <= 0:
        errors.append("original_tokens must be > 0")
    elif cs.get("compressed_tokens", 0) <= 0:
        errors.append("compressed_tokens must be > 0")
    elif cs.get("reduction_percent", -1) < 0:
        errors.append("reduction_percent must be >= 0")

    # Reasoning fields
    reasoning = data.get("reasoning", {})
    for field in REQUIRED_REASONING_FIELDS:
        if field not in reasoning:
            errors.append(f"Missing reasoning.{field}")

    # Latency breakdown
    lb = data.get("latency_breakdown", {})
    for field in ["ml_ms", "scaledown_ms", "llm_ms", "total_ms"]:
        if field not in lb:
            errors.append(f"Missing latency_breakdown.{field}")

    return errors


async def run_case(client: httpx.AsyncClient, case: dict) -> dict:
    payload = {
        "patient_data": {
            "vitals": case["vitals"],
            "age": case["age"],
            "symptoms": case["symptoms"],
        },
        "request_id": case["case_id"],
    }
    try:
        resp = await client.post(
            "http://localhost:8000/api/v1/ml/triage/predict",
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        errors = validate_response(data)
        return {
            "case_id": case["case_id"],
            "expected_severity": case["expected_severity"],
            "predicted_severity": data.get("risk_tier"),
            "compression_stats": data.get("compression_stats", {}),
            "latency_breakdown": data.get("latency_breakdown", {}),
            "gemini_reasoning": data.get("reasoning", {}).get("gemini_reasoning", False),
            "http_status": resp.status_code,
            "validation_errors": errors,
            "passed": len(errors) == 0,
        }
    except Exception as e:
        return {
            "case_id": case["case_id"],
            "expected_severity": case["expected_severity"],
            "http_status": None,
            "validation_errors": [f"Request failed: {e}"],
            "passed": False,
        }


async def main():
    with open("data/synthetic_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    cases = dataset["cases"]
    total = len(cases)
    print(f"Starting end-to-end validation: {total} cases")
    print(f"Distribution: {dataset['distribution']}")
    print()

    results = []
    async with httpx.AsyncClient() as client:
        for i, case in enumerate(cases, 1):
            print(f"[{i:3d}/{total}] {case['case_id']:<25}", end=" ", flush=True)
            result = await run_case(client, case)
            results.append(result)
            status = "PASS" if result["passed"] else f"FAIL: {result['validation_errors']}"
            cs = result.get("compression_stats", {})
            print(f"{status}  |  {cs.get('original_tokens','?')}→{cs.get('compressed_tokens','?')} tokens ({cs.get('reduction_percent','?')}%)")

    # Aggregate
    passed  = [r for r in results if r["passed"]]
    failed  = [r for r in results if not r["passed"]]
    success_rate = round(len(passed) / total * 100, 2)
    failure_rate = round(len(failed) / total * 100, 2)

    # Per-severity pass rate
    by_sev = {}
    for r in results:
        sev = r.get("expected_severity", "UNKNOWN")
        by_sev.setdefault(sev, {"pass": 0, "fail": 0})
        if r["passed"]:
            by_sev[sev]["pass"] += 1
        else:
            by_sev[sev]["fail"] += 1

    # Compression stats across passed cases
    reductions = [r["compression_stats"]["reduction_percent"] for r in passed if r.get("compression_stats")]
    avg_red = round(sum(reductions) / len(reductions), 2) if reductions else 0

    print()
    print("=" * 70)
    print("END-TO-END VALIDATION REPORT")
    print("=" * 70)
    print(f"Total cases:    {total}")
    print(f"Passed:         {len(passed)}  ({success_rate}%)")
    print(f"Failed:         {len(failed)}  ({failure_rate}%)")
    print(f"Avg compression:{avg_red}%")
    print()
    print("Per-severity pass rate:")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev not in by_sev:
            continue
        d = by_sev[sev]
        total_sev = d["pass"] + d["fail"]
        pct = round(d["pass"] / total_sev * 100, 1)
        print(f"  {sev:<10} {d['pass']}/{total_sev}  ({pct}%)")

    if failed:
        print()
        print("FAILURES:")
        for r in failed:
            print(f"  {r['case_id']}: {r['validation_errors']}")

    # Save report
    report = {
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "total_cases": total,
        "passed": len(passed),
        "failed": len(failed),
        "success_rate_pct": success_rate,
        "failure_rate_pct": failure_rate,
        "avg_compression_pct": avg_red,
        "per_severity": {
            sev: {
                "pass": by_sev.get(sev, {}).get("pass", 0),
                "fail": by_sev.get(sev, {}).get("fail", 0),
                "pass_rate_pct": round(by_sev.get(sev, {}).get("pass", 0) / max(1, by_sev.get(sev, {}).get("pass", 0) + by_sev.get(sev, {}).get("fail", 0)) * 100, 1),
            }
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        },
        "failures": [{"case_id": r["case_id"], "errors": r["validation_errors"]} for r in failed],
        "results": results,
    }

    with open("data/validation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print()
    print(f"Report saved to data/validation_report.json")
    print()
    if failure_rate == 0.0:
        print("✓ VALIDATION PASSED — 0% failure rate")
    else:
        print(f"✗ VALIDATION FAILED — {failure_rate}% failure rate")


if __name__ == "__main__":
    asyncio.run(main())
