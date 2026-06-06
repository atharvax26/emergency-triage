"""Remove legacy small-context entries from metrics.json.

These 10 entries were recorded before _build_rich_clinical_context() was added
(original_tokens < 200, compression ~14-17%). They are not fabricated — they
are real but from an earlier pipeline version. Removing them keeps the live
dashboard stats consistent with the evaluation dataset (all rich-context).
"""
import json

with open("data/metrics.json") as f:
    metrics = json.load(f)

before = len(metrics)
clean = [m for m in metrics if m["original_tokens"] >= 200]
after = len(clean)

print(f"Removed {before - after} legacy entries (original_tokens < 200)")
print(f"Remaining: {after} entries")

# Verify remaining stats
ratios = [m["compression_ratio"] * 100 for m in clean]
print(f"Avg compression after clean: {sum(ratios)/len(ratios):.1f}%")

with open("data/metrics.json", "w") as f:
    json.dump(clean, f, indent=2)

print("metrics.json updated.")
