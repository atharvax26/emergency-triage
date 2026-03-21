"""
Batch evaluation script for Scaledown compression performance.
Runs all 150 synthetic cases through the pipeline and aggregates results.
"""

import json
import httpx
import asyncio
from datetime import datetime


async def evaluate_case(client: httpx.AsyncClient, case: dict) -> dict:
    """Run a single case through the prediction endpoint."""
    payload = {
        "patient_data": {
            "vitals": case["vitals"],
            "age": case["age"],
            "symptoms": case["symptoms"],
        },
        "request_id": case["case_id"],
    }
    
    try:
        response = await client.post(
            "http://localhost:8000/api/v1/ml/triage/predict",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        
        return {
            "case_id": case["case_id"],
            "expected_severity": case["expected_severity"],
            "predicted_severity": result.get("risk_tier", "UNKNOWN"),
            "compression_stats": result.get("compression_stats", {}),
            "latency_breakdown": result.get("latency_breakdown", {}),
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "case_id": case["case_id"],
            "expected_severity": case["expected_severity"],
            "success": False,
            "error": str(e),
        }


async def main():
    """Run batch evaluation."""
    
    # Load dataset
    with open("data/synthetic_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    cases = dataset["cases"]
    print(f"Loaded {len(cases)} cases")
    print(f"Distribution: {dataset['distribution']}")
    print()
    
    # Run evaluation
    results = []
    async with httpx.AsyncClient() as client:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] Evaluating {case['case_id']}...", end=" ", flush=True)
            result = await evaluate_case(client, case)
            results.append(result)
            
            if result["success"]:
                cs = result["compression_stats"]
                print(f"{cs.get('original_tokens', '?')} → {cs.get('compressed_tokens', '?')} tokens ({cs.get('reduction_percent', '?')}%)")
            else:
                print(f"FAILED: {result['error']}")
    
    # Aggregate statistics
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print()
    print("=" * 80)
    print(f"EVALUATION COMPLETE: {len(successful)}/{len(cases)} successful")
    print("=" * 80)
    
    if not successful:
        print("No successful cases to analyze")
        return
    
    # Overall compression stats
    total_orig = sum(r["compression_stats"]["original_tokens"] for r in successful)
    total_comp = sum(r["compression_stats"]["compressed_tokens"] for r in successful)
    avg_reduction = sum(r["compression_stats"]["reduction_percent"] for r in successful) / len(successful)
    
    print(f"\nOVERALL COMPRESSION:")
    print(f"  Total original tokens:    {total_orig:,}")
    print(f"  Total compressed tokens:  {total_comp:,}")
    print(f"  Average reduction:        {avg_reduction:.1f}%")
    print(f"  Total tokens saved:       {total_orig - total_comp:,}")
    
    # Per-severity breakdown
    by_severity = {}
    for r in successful:
        sev = r["expected_severity"]
        if sev not in by_severity:
            by_severity[sev] = []
        by_severity[sev].append(r)
    
    print(f"\nPER-SEVERITY BREAKDOWN:")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev not in by_severity:
            continue
        cases_sev = by_severity[sev]
        avg_orig = sum(c["compression_stats"]["original_tokens"] for c in cases_sev) / len(cases_sev)
        avg_comp = sum(c["compression_stats"]["compressed_tokens"] for c in cases_sev) / len(cases_sev)
        avg_red = sum(c["compression_stats"]["reduction_percent"] for c in cases_sev) / len(cases_sev)
        
        print(f"  {sev:8s} ({len(cases_sev):3d} cases): {avg_orig:6.0f} → {avg_comp:6.0f} tokens ({avg_red:5.1f}% reduction)")
    
    # Latency breakdown
    avg_ml = sum(r["latency_breakdown"].get("ml_ms", 0) for r in successful) / len(successful)
    avg_scaledown = sum(r["latency_breakdown"].get("scaledown_ms", 0) for r in successful) / len(successful)
    avg_llm = sum(r["latency_breakdown"].get("llm_ms", 0) for r in successful) / len(successful)
    avg_total = sum(r["latency_breakdown"].get("total_ms", 0) for r in successful) / len(successful)
    
    print(f"\nLATENCY BREAKDOWN:")
    print(f"  ML inference:       {avg_ml:7.2f}ms")
    print(f"  Scaledown pruning:  {avg_scaledown:7.2f}ms")
    print(f"  LLM reasoning:      {avg_llm:7.2f}ms")
    print(f"  Total pipeline:     {avg_total:7.2f}ms")
    
    # Save results
    output = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "total_cases": len(cases),
        "successful": len(successful),
        "failed": len(failed),
        "overall_stats": {
            "total_original_tokens": total_orig,
            "total_compressed_tokens": total_comp,
            "average_reduction_percent": round(avg_reduction, 2),
            "total_tokens_saved": total_orig - total_comp,
        },
        "per_severity_stats": {
            sev: {
                "count": len(by_severity.get(sev, [])),
                "avg_original_tokens": round(sum(c["compression_stats"]["original_tokens"] for c in by_severity.get(sev, [])) / len(by_severity.get(sev, [1])), 1) if sev in by_severity else 0,
                "avg_compressed_tokens": round(sum(c["compression_stats"]["compressed_tokens"] for c in by_severity.get(sev, [])) / len(by_severity.get(sev, [1])), 1) if sev in by_severity else 0,
                "avg_reduction_percent": round(sum(c["compression_stats"]["reduction_percent"] for c in by_severity.get(sev, [])) / len(by_severity.get(sev, [1])), 1) if sev in by_severity else 0,
            }
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        },
        "latency_stats": {
            "avg_ml_ms": round(avg_ml, 2),
            "avg_scaledown_ms": round(avg_scaledown, 2),
            "avg_llm_ms": round(avg_llm, 2),
            "avg_total_ms": round(avg_total, 2),
        },
        "results": results,
    }
    
    with open("data/compression_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to data/compression_evaluation.json")


if __name__ == "__main__":
    asyncio.run(main())
