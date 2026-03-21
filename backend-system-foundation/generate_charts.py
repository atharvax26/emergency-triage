"""
Generate visual evidence charts from evaluation data.
Outputs 3 PNG files to data/charts/:
  1. before_after_tokens.png  — grouped bar chart by severity
  2. reduction_histogram.png  — distribution of reduction % across 150 cases
  3. latency_breakdown.png    — stacked bar chart: ML / Scaledown / LLM per severity
"""

import json
import os
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

os.makedirs("data/charts", exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with open("data/compression_evaluation.json", "r", encoding="utf-8") as f:
    eval_data = json.load(f)

results = [r for r in eval_data["results"] if r["success"]]

# ── Colour palette ────────────────────────────────────────────────────────────
SEV_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#eab308",
    "LOW":      "#22c55e",
}
SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

DARK_BG   = "#0f172a"
CARD_BG   = "#1e293b"
TEXT_COL  = "#f1f5f9"
MUTED     = "#94a3b8"
ACCENT    = "#facc15"

def apply_dark(fig, axes):
    fig.patch.set_facecolor(DARK_BG)
    for ax in (axes if hasattr(axes, "__iter__") else [axes]):
        ax.set_facecolor(CARD_BG)
        ax.tick_params(colors=TEXT_COL)
        ax.xaxis.label.set_color(TEXT_COL)
        ax.yaxis.label.set_color(TEXT_COL)
        ax.title.set_color(TEXT_COL)
        for spine in ax.spines.values():
            spine.set_edgecolor("#334155")


# ═══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Before vs After tokens (grouped bar by severity)
# ═══════════════════════════════════════════════════════════════════════════════
by_sev = {s: {"orig": [], "comp": []} for s in SEV_ORDER}
for r in results:
    sev = r["expected_severity"]
    if sev in by_sev:
        by_sev[sev]["orig"].append(r["compression_stats"]["original_tokens"])
        by_sev[sev]["comp"].append(r["compression_stats"]["compressed_tokens"])

avg_orig = [sum(by_sev[s]["orig"]) / len(by_sev[s]["orig"]) for s in SEV_ORDER]
avg_comp = [sum(by_sev[s]["comp"]) / len(by_sev[s]["comp"]) for s in SEV_ORDER]
counts   = [len(by_sev[s]["orig"]) for s in SEV_ORDER]

x = np.arange(len(SEV_ORDER))
w = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
apply_dark(fig, ax)

bars_orig = ax.bar(x - w/2, avg_orig, w, label="Before Pruning", color="#475569", zorder=3)
bars_comp = ax.bar(x + w/2, avg_comp, w, label="After Pruning",  color=ACCENT,   zorder=3)

# Reduction % labels above each pair
for i, (o, c) in enumerate(zip(avg_orig, avg_comp)):
    pct = round((1 - c / o) * 100, 1)
    ax.text(x[i], max(o, c) + 20, f"−{pct}%", ha="center", va="bottom",
            color=ACCENT, fontsize=11, fontweight="bold")

# Count labels inside bars
for i, (bar, cnt) in enumerate(zip(bars_orig, counts)):
    ax.text(bar.get_x() + bar.get_width()/2, 30, f"n={cnt}",
            ha="center", va="bottom", color=TEXT_COL, fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels([f"{s}\n({c} cases)" for s, c in zip(SEV_ORDER, counts)], color=TEXT_COL)
ax.set_ylabel("Avg Tokens", color=TEXT_COL)
ax.set_title("Before vs After Scaledown Pruning — by Severity", color=TEXT_COL, fontsize=14, pad=15)
ax.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, framealpha=0.8)
ax.yaxis.grid(True, color="#334155", linestyle="--", alpha=0.5, zorder=0)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("data/charts/before_after_tokens.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ before_after_tokens.png")


# ═══════════════════════════════════════════════════════════════════════════════
# CHART 2 — Reduction % histogram
# ═══════════════════════════════════════════════════════════════════════════════
all_reductions = [r["compression_stats"]["reduction_percent"] for r in results]
mean_r = sum(all_reductions) / len(all_reductions)
variance = sum((x - mean_r)**2 for x in all_reductions) / len(all_reductions)
std_r = math.sqrt(variance)
min_r = min(all_reductions)
max_r = max(all_reductions)

fig, ax = plt.subplots(figsize=(10, 6))
apply_dark(fig, ax)

n_bins = 20
counts_h, edges, patches = ax.hist(all_reductions, bins=n_bins, color=ACCENT, edgecolor=DARK_BG, zorder=3)

# Colour bars by severity zone
for patch, left in zip(patches, edges[:-1]):
    if left < 40:
        patch.set_facecolor("#ef4444")
    elif left < 60:
        patch.set_facecolor("#f97316")
    elif left < 70:
        patch.set_facecolor("#eab308")
    else:
        patch.set_facecolor("#22c55e")

# Mean line
ax.axvline(mean_r, color="#38bdf8", linewidth=2, linestyle="--", zorder=4, label=f"Mean {mean_r:.1f}%")
ax.axvline(mean_r - std_r, color="#94a3b8", linewidth=1, linestyle=":", zorder=4, label=f"±1σ ({std_r:.1f}%)")
ax.axvline(mean_r + std_r, color="#94a3b8", linewidth=1, linestyle=":", zorder=4)

ax.set_xlabel("Reduction %", color=TEXT_COL)
ax.set_ylabel("Number of Cases", color=TEXT_COL)
ax.set_title(f"Token Reduction Distribution (n={len(all_reductions)})", color=TEXT_COL, fontsize=14, pad=15)

stats_text = f"Mean: {mean_r:.1f}%\nStd: ±{std_r:.1f}%\nMin: {min_r:.1f}%\nMax: {max_r:.1f}%"
ax.text(0.02, 0.97, stats_text, transform=ax.transAxes, va="top", ha="left",
        color=TEXT_COL, fontsize=10,
        bbox=dict(boxstyle="round,pad=0.4", facecolor=DARK_BG, edgecolor="#334155", alpha=0.9))

ax.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, framealpha=0.8)
ax.yaxis.grid(True, color="#334155", linestyle="--", alpha=0.5, zorder=0)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("data/charts/reduction_histogram.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ reduction_histogram.png")


# ═══════════════════════════════════════════════════════════════════════════════
# CHART 3 — Latency breakdown (stacked bar by severity)
# ═══════════════════════════════════════════════════════════════════════════════
lat_by_sev = {s: {"ml": [], "scaledown": [], "llm": []} for s in SEV_ORDER}
for r in results:
    sev = r["expected_severity"]
    lb  = r.get("latency_breakdown", {})
    if sev in lat_by_sev and lb:
        lat_by_sev[sev]["ml"].append(lb.get("ml_ms", 0))
        lat_by_sev[sev]["scaledown"].append(lb.get("scaledown_ms", 0))
        lat_by_sev[sev]["llm"].append(lb.get("llm_ms", 0))

avg_ml  = [sum(lat_by_sev[s]["ml"])       / max(1, len(lat_by_sev[s]["ml"]))       for s in SEV_ORDER]
avg_sd  = [sum(lat_by_sev[s]["scaledown"]) / max(1, len(lat_by_sev[s]["scaledown"])) for s in SEV_ORDER]
avg_llm = [sum(lat_by_sev[s]["llm"])      / max(1, len(lat_by_sev[s]["llm"]))      for s in SEV_ORDER]

fig, ax = plt.subplots(figsize=(10, 6))
apply_dark(fig, ax)

x = np.arange(len(SEV_ORDER))
w = 0.5

b1 = ax.bar(x, avg_ml,  w, label="ML Inference",       color="#38bdf8", zorder=3)
b2 = ax.bar(x, avg_sd,  w, label="Scaledown Pruning",  color="#a78bfa", bottom=avg_ml, zorder=3)
b3 = ax.bar(x, avg_llm, w, label="LLM Reasoning",      color="#fb923c",
            bottom=[m + s for m, s in zip(avg_ml, avg_sd)], zorder=3)

# Total labels on top
for i, (m, s, l) in enumerate(zip(avg_ml, avg_sd, avg_llm)):
    total = m + s + l
    ax.text(i, total + 30, f"{total:.0f}ms", ha="center", va="bottom",
            color=TEXT_COL, fontsize=10, fontweight="bold")

# ML value inside bar (tiny)
for i, m in enumerate(avg_ml):
    if m > 5:
        ax.text(i, m / 2, f"{m:.1f}ms", ha="center", va="center",
                color=DARK_BG, fontsize=8, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(SEV_ORDER, color=TEXT_COL)
ax.set_ylabel("Avg Latency (ms)", color=TEXT_COL)
ax.set_title("Pipeline Latency Breakdown by Severity", color=TEXT_COL, fontsize=14, pad=15)
ax.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, framealpha=0.8)
ax.yaxis.grid(True, color="#334155", linestyle="--", alpha=0.5, zorder=0)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("data/charts/latency_breakdown.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ latency_breakdown.png")

print()
print("All charts saved to data/charts/")
