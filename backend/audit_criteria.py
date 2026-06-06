import json
from collections import Counter

with open("data/metrics.json") as f:
    metrics = json.load(f)

old = [m for m in metrics if m["original_tokens"] < 200]
new = [m for m in metrics if m["original_tokens"] >= 200]

print(f"Total metrics entries: {len(metrics)}")
print(f"Old small-context entries (< 200 tokens): {len(old)}")
print(f"New rich-context entries (>= 200 tokens): {len(new)}")

if new:
    ratios = [m["compression_ratio"] * 100 for m in new]
    print(f"New entries avg compression: {sum(ratios)/len(ratios):.1f}%")
    print(f"New entries min compression: {min(ratios):.1f}%")
    print(f"New entries max compression: {max(ratios):.1f}%")
    has_latency = [m for m in new if "scaledown_ms" in m and "llm_ms" in m]
    print(f"New entries with full latency breakdown: {len(has_latency)}/{len(new)}")
    sev = Counter(m["severity"] for m in new)
    print(f"Severity distribution: {dict(sev)}")

with open("data/compression_evaluation.json") as f:
    ev = json.load(f)

print()
print("=== EVALUATION DATA ===")
print(f"Total cases: {ev['total_cases']}")
print(f"Successful: {ev['successful']}, Failed: {ev['failed']}")
print(f"Avg reduction: {ev['overall_stats']['average_reduction_percent']}%")
print(f"Total tokens saved: {ev['overall_stats']['total_tokens_saved']:,}")
print("Per severity:")
for sev_name, s in ev["per_severity_stats"].items():
    print(f"  {sev_name}: {s['count']} cases, {s['avg_reduction_percent']}% avg reduction")
ls = ev["latency_stats"]
print(f"Latency: ML={ls['avg_ml_ms']}ms, Scaledown={ls['avg_scaledown_ms']}ms, LLM={ls['avg_llm_ms']}ms, Total={ls['avg_total_ms']}ms")

with open("data/validation_report.json") as f:
    vr = json.load(f)

print()
print("=== VALIDATION REPORT ===")
print(f"Total: {vr['total_cases']}, Passed: {vr['passed']}, Failed: {vr['failed']}")
print(f"Success rate: {vr['success_rate_pct']}%")
print("Per severity pass rates:")
for sev_name, d in vr["per_severity"].items():
    print(f"  {sev_name}: {d['pass']}/{d['pass']+d['fail']} ({d['pass_rate_pct']}%)")
