"""
Full diagnostic script for Emergency Triage System.
Tests: data files, ML predictor, Scaledown pruner, Gemini reasoner,
       API endpoints, compression pipeline, metrics integrity.
"""
import asyncio, json, os, sys, time, importlib.util, pathlib

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
results = []

def check(name, status, detail=""):
    icon = "✅" if status == PASS else ("⚠️ " if status == WARN else "❌")
    results.append((status, name, detail))
    print(f"  {icon} [{status}] {name}" + (f" — {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ── 1. Data files ─────────────────────────────────────────────
section("1. DATA FILES")
DATA = pathlib.Path("data")
required_files = [
    "compression_evaluation.json",
    "validation_report.json",
    "metrics.json",
    "synthetic_dataset.json",
    "determinism_proof.json",
]
for fname in required_files:
    p = DATA / fname
    if p.exists():
        size = p.stat().st_size
        check(fname, PASS, f"{size:,} bytes")
    else:
        check(fname, FAIL, "missing")

# ── 2. Evaluation data integrity ──────────────────────────────
section("2. EVALUATION DATA INTEGRITY")
try:
    with open(DATA / "compression_evaluation.json") as f:
        ev = json.load(f)
    check("total_cases == 150", PASS if ev["total_cases"] == 150 else FAIL, str(ev["total_cases"]))
    check("failed == 0", PASS if ev["failed"] == 0 else FAIL, str(ev["failed"]))
    avg = ev["overall_stats"]["average_reduction_percent"]
    check(f"avg compression >= 25%", PASS if avg >= 25 else FAIL, f"{avg}%")
    check(f"avg compression >= 65%", PASS if avg >= 65 else WARN, f"{avg}%")
    saved = ev["overall_stats"]["total_tokens_saved"]
    check(f"total_tokens_saved", PASS, f"{saved:,}")
    sevs = list(ev["per_severity_stats"].keys())
    for s in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        check(f"severity {s} present", PASS if s in sevs else FAIL,
              f"{ev['per_severity_stats'].get(s,{}).get('count',0)} cases" if s in sevs else "missing")
    ls = ev["latency_stats"]
    check("latency_stats present", PASS,
          f"ML={ls['avg_ml_ms']}ms Scaledown={ls['avg_scaledown_ms']}ms LLM={ls['avg_llm_ms']}ms Total={ls['avg_total_ms']}ms")
except Exception as e:
    check("compression_evaluation.json parse", FAIL, str(e))

# ── 3. Validation report ──────────────────────────────────────
section("3. VALIDATION REPORT")
try:
    with open(DATA / "validation_report.json") as f:
        vr = json.load(f)
    check("success_rate == 100%", PASS if vr["success_rate_pct"] == 100.0 else FAIL,
          f"{vr['success_rate_pct']}%")
    check("failure_rate == 0%", PASS if vr["failure_rate_pct"] == 0.0 else FAIL,
          f"{vr['failure_rate_pct']}%")
    for s, d in vr["per_severity"].items():
        check(f"{s} pass rate", PASS if d["pass_rate_pct"] == 100.0 else FAIL,
              f"{d['pass']}/{d['pass']+d['fail']}")
except Exception as e:
    check("validation_report.json parse", FAIL, str(e))

# ── 4. Metrics integrity ──────────────────────────────────────
section("4. LIVE METRICS INTEGRITY")
try:
    with open(DATA / "metrics.json") as f:
        metrics = json.load(f)
    total = len(metrics)
    check("total entries", PASS, str(total))
    old = [m for m in metrics if m["original_tokens"] < 200]
    check("no legacy small-context entries", PASS if len(old) == 0 else WARN,
          f"{len(old)} entries with <200 tokens")
    ratios = [m["compression_ratio"]*100 for m in metrics if m["original_tokens"] >= 200]
    if ratios:
        avg_r = sum(ratios)/len(ratios)
        check(f"avg compression ratio", PASS if avg_r >= 60 else FAIL, f"{avg_r:.1f}%")
        check(f"min compression ratio >= 25%", PASS if min(ratios) >= 25 else FAIL, f"{min(ratios):.1f}%")
    has_lat = [m for m in metrics if "scaledown_ms" in m and "llm_ms" in m]
    check("entries with full latency breakdown",
          PASS if len(has_lat) == total else WARN,
          f"{len(has_lat)}/{total}")
    from collections import Counter
    sev_dist = Counter(m["severity"] for m in metrics)
    check("CRITICAL entries in live metrics", PASS if sev_dist.get("CRITICAL",0) > 0 else WARN,
          str(sev_dist.get("CRITICAL",0)))
    check("severity distribution", PASS, dict(sev_dist))
except Exception as e:
    check("metrics.json parse", FAIL, str(e))

# ── 5. ML Predictor ───────────────────────────────────────────
section("5. ML PREDICTOR (SimplePredictor)")
try:
    ml_path = str(pathlib.Path("../ml-pipeline/src/api").resolve())
    if ml_path not in sys.path:
        sys.path.insert(0, ml_path)
    from simple_predictor import SimplePredictor
    pred = SimplePredictor()
    check("SimplePredictor import", PASS)
    test_input = {
        "heart_rate": 120, "systolic_bp": 85, "diastolic_bp": 55,
        "temperature": 39.8, "spo2": 88, "respiratory_rate": 28,
        "age": 65, "symptoms": ["chest pain", "shortness of breath"]
    }
    t0 = time.perf_counter()
    result = pred.predict(test_input)
    ml_ms = round((time.perf_counter()-t0)*1000, 2)
    check("predict() returns result", PASS if result else FAIL)
    check("risk_tier present", PASS if "risk_tier" in result else FAIL,
          result.get("risk_tier","missing"))
    check("confidence present", PASS if "confidence" in result else FAIL,
          str(result.get("confidence","")))
    check("ML inference time", PASS if ml_ms < 100 else WARN, f"{ml_ms}ms")
    # CRITICAL case
    crit_input = {**test_input, "spo2": 82, "systolic_bp": 70, "heart_rate": 140}
    crit = pred.predict(crit_input)
    check("CRITICAL case detected", PASS if crit.get("risk_tier") in ["CRITICAL","HIGH"] else WARN,
          crit.get("risk_tier","?"))
    # LOW case
    low_input = {"heart_rate": 72, "systolic_bp": 118, "diastolic_bp": 76,
                 "temperature": 37.0, "spo2": 99, "respiratory_rate": 14,
                 "age": 25, "symptoms": ["mild headache"]}
    low = pred.predict(low_input)
    check("LOW case detected", PASS if low.get("risk_tier") in ["LOW","MEDIUM"] else WARN,
          low.get("risk_tier","?"))
except Exception as e:
    check("SimplePredictor", FAIL, str(e))

# ── 6. Scaledown Pruner ───────────────────────────────────────
section("6. SCALEDOWN PRUNER")
async def test_pruner():
    try:
        spec = importlib.util.spec_from_file_location(
            "scaledown_pruner", pathlib.Path("app/scaledown_pruner.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pruner = mod.get_pruner()
        check("ScaledownPruner import", PASS)
        check("API key configured", PASS if pruner._enabled else WARN,
              "enabled" if pruner._enabled else "no key — passthrough mode")
        # Build rich context
        long_ctx = ("Patient presents with severe chest pain radiating to left arm. "
                    "History of hypertension, diabetes. Vitals: BP 85/55, HR 140, SpO2 88%, "
                    "Temp 39.8C, RR 28. Previous MI in 2019. On aspirin, metformin. "
                    "Nurse notes: diaphoretic, pale, confused. ") * 20
        t0 = time.perf_counter()
        r = await pruner.prune(context=long_ctx, prompt="Summarize for triage.")
        sd_ms = round((time.perf_counter()-t0)*1000, 2)
        check("prune() returns result", PASS if r else FAIL)
        check("original_tokens present", PASS if "original_tokens" in r else FAIL,
              str(r.get("original_tokens","")))
        check("compressed_tokens present", PASS if "compressed_tokens" in r else FAIL,
              str(r.get("compressed_tokens","")))
        ratio = r.get("compression_ratio", 0) * 100
        applied = r.get("pruning_applied", False)
        check("pruning_applied", PASS if applied else WARN,
              "True" if applied else "False (passthrough)")
        check(f"compression ratio", PASS if ratio >= 25 else WARN, f"{ratio:.1f}%")
        check(f"Scaledown latency", PASS if sd_ms < 5000 else WARN, f"{sd_ms}ms")
        check(f"compressed_context present",
              PASS if r.get("compressed_context") else FAIL)
    except Exception as e:
        check("ScaledownPruner", FAIL, str(e))

asyncio.run(test_pruner())

# ── 7. Gemini Reasoner ────────────────────────────────────────
section("7. GEMINI REASONER")
async def test_gemini():
    try:
        spec = importlib.util.spec_from_file_location(
            "gemini_reasoner", pathlib.Path("app/gemini_reasoner.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        check("gemini_reasoner import", PASS)
        available = mod.is_available()
        check("Gemini API key configured", PASS if available else WARN,
              "available" if available else "not available — rule-based fallback active")
        t0 = time.perf_counter()
        r = await mod.reason(
            compressed_context="Patient: 65yo, BP 85/55, HR 140, SpO2 88%, chest pain.",
            risk_tier="CRITICAL", confidence=0.92,
            calibrated_probability=0.91, age=65,
            symptoms=["chest pain", "shortness of breath"]
        )
        llm_ms = round((time.perf_counter()-t0)*1000, 2)
        check("reason() returns result", PASS if r else FAIL)
        for field in ["severity_justification","recommended_actions","reasoning_trace",
                      "clinical_priority","estimated_wait_minutes","gemini_reasoning"]:
            check(f"field: {field}", PASS if field in r else FAIL,
                  str(r.get(field,"missing"))[:60])
        check("Gemini LLM latency", PASS if llm_ms < 15000 else WARN, f"{llm_ms}ms")
        check("gemini_reasoning flag", PASS if available == r.get("gemini_reasoning") else WARN,
              str(r.get("gemini_reasoning")))
    except Exception as e:
        check("Gemini reasoner", FAIL, str(e))

asyncio.run(test_gemini())

# ── 8. Full pipeline (end-to-end) ─────────────────────────────
section("8. FULL PIPELINE (end-to-end)")
async def test_pipeline():
    try:
        spec_p = importlib.util.spec_from_file_location(
            "scaledown_pruner", pathlib.Path("app/scaledown_pruner.py"))
        mod_p = importlib.util.module_from_spec(spec_p)
        spec_p.loader.exec_module(mod_p)

        spec_g = importlib.util.spec_from_file_location(
            "gemini_reasoner", pathlib.Path("app/gemini_reasoner.py"))
        mod_g = importlib.util.module_from_spec(spec_g)
        spec_g.loader.exec_module(mod_g)

        spec_m = importlib.util.spec_from_file_location(
            "main_simple", pathlib.Path("app/main_simple.py"))
        mod_m = importlib.util.module_from_spec(spec_m)
        spec_m.loader.exec_module(mod_m)

        build_ctx = mod_m._build_rich_clinical_context

        cases = [
            ("CRITICAL — Sepsis", 72, {"systolic_bp":78,"diastolic_bp":48,"heart_rate":138,
             "respiratory_rate":32,"temperature":39.9,"spo2":87},
             ["fever","confusion","rapid breathing","low blood pressure"]),
            ("HIGH — Chest Pain", 58, {"systolic_bp":145,"diastolic_bp":92,"heart_rate":108,
             "respiratory_rate":22,"temperature":37.2,"spo2":94},
             ["chest pain","shortness of breath","diaphoresis"]),
            ("MEDIUM — Abdominal", 34, {"systolic_bp":122,"diastolic_bp":78,"heart_rate":88,
             "respiratory_rate":16,"temperature":37.8,"spo2":97},
             ["abdominal pain","nausea","vomiting"]),
            ("LOW — Headache", 28, {"systolic_bp":118,"diastolic_bp":74,"heart_rate":70,
             "respiratory_rate":14,"temperature":36.9,"spo2":99},
             ["mild headache","fatigue"]),
        ]

        class FakeVitals:
            def __init__(self, d):
                for k,v in d.items(): setattr(self, k, v)

        for label, age, vitals_d, symptoms in cases:
            vitals = FakeVitals(vitals_d)
            t0 = time.perf_counter()
            ctx = build_ctx(age, vitals, symptoms)
            orig_tokens = len(ctx.split())
            pruner = mod_p.get_pruner()
            pr = await pruner.prune(context=ctx, prompt="Summarize for triage.")
            comp_tokens = pr["compressed_tokens"]
            ratio = pr["compression_ratio"]*100
            gr = await mod_g.reason(
                compressed_context=pr["compressed_context"],
                risk_tier="CRITICAL" if "CRITICAL" in label else
                          "HIGH" if "HIGH" in label else
                          "MEDIUM" if "MEDIUM" in label else "LOW",
                confidence=0.88, calibrated_probability=0.87,
                age=age, symptoms=symptoms
            )
            total_ms = round((time.perf_counter()-t0)*1000, 2)
            check(f"{label}",
                  PASS if ratio >= 25 and gr.get("severity_justification") else WARN,
                  f"orig={orig_tokens} comp={comp_tokens} reduction={ratio:.1f}% total={total_ms}ms")
    except Exception as e:
        check("Full pipeline", FAIL, str(e))

asyncio.run(test_pipeline())

# ── 9. API endpoints (live backend) ──────────────────────────
section("9. LIVE API ENDPOINTS (requires backend running on :8000)")
import urllib.request, urllib.error

def http_get(url, timeout=4):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)

BASE = "http://localhost:8000"
endpoints = [
    ("/health",              "health check"),
    ("/api/v1/ml/health",    "ML health"),
    ("/api/v1/stats",        "stats endpoint"),
    ("/api/v1/evaluation",   "evaluation endpoint"),
    ("/api/v1/audit",        "audit log"),
    ("/api/v1/queue",        "queue"),
    ("/api/v1/patients",     "patients"),
]
backend_up = False
for path, label in endpoints:
    data, status = http_get(BASE + path)
    if status == 200:
        if not backend_up and path == "/health":
            backend_up = True
        detail = ""
        if path == "/api/v1/ml/health" and data:
            detail = f"gemini_reasoning={data.get('gemini_reasoning')} ml_service={data.get('ml_service')}"
        elif path == "/api/v1/stats" and data:
            detail = f"predictions={data.get('total_predictions')} avg_reduction={data.get('avg_tokens_saved_pct')}%"
        elif path == "/api/v1/evaluation" and data:
            detail = f"cases={data.get('total_cases')} avg_reduction={data.get('overall_stats',{}).get('average_reduction_percent')}%"
        elif path == "/api/v1/audit" and data:
            detail = f"entries={data.get('total',0)}"
        check(f"GET {path} ({label})", PASS, detail or f"HTTP {status}")
    else:
        check(f"GET {path} ({label})",
              WARN if not backend_up else FAIL,
              f"HTTP {status} — start backend first" if not backend_up else f"HTTP {status}")

# ── 10. Frontend TypeScript diagnostics ──────────────────────
section("10. FRONTEND SOURCE FILES")
fe_src = pathlib.Path("../emergency-triage/src")
critical_files = [
    "pages/Dashboard.tsx",
    "pages/AuditLog.tsx",
    "pages/Index.tsx",
    "components/CompressionCharts.tsx",
    "lib/api.ts",
    "lib/mock-data.ts",
    "hooks/use-auth.ts",
    "lib/permissions.ts",
]
for f in critical_files:
    p = fe_src / f
    if p.exists():
        size = p.stat().st_size
        check(f"src/{f}", PASS, f"{size:,} bytes")
    else:
        check(f"src/{f}", FAIL, "missing")

# Check CompressionCharts has recharts imports
charts = fe_src / "components/CompressionCharts.tsx"
if charts.exists():
    content = charts.read_text()
    check("CompressionCharts uses recharts", PASS if "recharts" in content else FAIL)
    check("CompressionCharts fetches /api/v1/evaluation",
          PASS if "getEvaluation" in content else FAIL)
    check("CompressionCharts has 3 charts",
          PASS if content.count("BarChart") >= 3 else WARN,
          f"{content.count('BarChart')} BarChart instances")

# Check api.ts has getEvaluation
api_ts = fe_src / "lib/api.ts"
if api_ts.exists():
    content = api_ts.read_text()
    check("api.ts has getEvaluation()", PASS if "getEvaluation" in content else FAIL)
    check("api.ts has latency_breakdown type", PASS if "latency_breakdown" in content else FAIL)
    check("api.ts has compression_stats type", PASS if "compression_stats" in content else FAIL)

# Check Dashboard has CompressionCharts
dash = fe_src / "pages/Dashboard.tsx"
if dash.exists():
    content = dash.read_text()
    check("Dashboard imports CompressionCharts", PASS if "CompressionCharts" in content else FAIL)
    check("Dashboard renders <CompressionCharts />",
          PASS if "<CompressionCharts" in content else FAIL)
    check("Dashboard has no Queue card",
          PASS if "Current Queue" not in content else FAIL)

# Check AuditLog has dialog
audit = fe_src / "pages/AuditLog.tsx"
if audit.exists():
    content = audit.read_text()
    check("AuditLog has Dialog", PASS if "Dialog" in content else FAIL)
    check("AuditLog row onClick", PASS if "onClick" in content else FAIL)
    check("AuditLog has DetailRow", PASS if "DetailRow" in content else FAIL)

# ── 11. Backend source integrity ──────────────────────────────
section("11. BACKEND SOURCE INTEGRITY")
main_py = pathlib.Path("app/main_simple.py")
if main_py.exists():
    content = main_py.read_text()
    checks = [
        ("_build_rich_clinical_context defined", "_build_rich_clinical_context" in content),
        ("predict_triage endpoint", "predict_triage" in content),
        ("compression_stats in response", '"compression_stats"' in content),
        ("latency_breakdown in response", '"latency_breakdown"' in content),
        ("[SCALEDOWN] print log", "[SCALEDOWN]" in content),
        ("[LATENCY] log lines", "[LATENCY]" in content),
        ("get_stats endpoint", "get_stats" in content),
        ("get_evaluation endpoint", "get_evaluation" in content),
        ("p50/p95 latency in stats", "p50_latency_ms" in content),
        ("compression_statistics in stats", "compression_statistics" in content),
        ("per_severity_breakdown in stats", "per_severity_breakdown" in content),
        ("reset endpoint", "reset_all_data" in content),
        ("audit log endpoint", "get_audit_log" in content),
        ("JWT auth", "_make_token" in content),
        ("CORS middleware", "CORSMiddleware" in content),
    ]
    for label, ok in checks:
        check(label, PASS if ok else FAIL)
else:
    check("app/main_simple.py", FAIL, "missing")

# ── 12. Requirements & env ────────────────────────────────────
section("12. REQUIREMENTS & ENVIRONMENT")
req = pathlib.Path("requirements.txt")
if req.exists():
    content = req.read_text()
    pkgs = ["fastapi", "uvicorn", "httpx", "google-genai", "python-jose", "bcrypt", "pydantic"]
    for pkg in pkgs:
        check(f"requirements.txt has {pkg}", PASS if pkg in content else FAIL)
else:
    check("requirements.txt", FAIL, "missing")

env = pathlib.Path(".env")
if env.exists():
    content = env.read_text()
    check(".env exists", PASS)
    check("SCALEDOWN_API_KEY in .env",
          PASS if "SCALEDOWN_API_KEY" in content and "=" in content else WARN)
    check("GEMINI_API_KEY in .env",
          PASS if "GEMINI_API_KEY" in content else WARN)
else:
    check(".env file", WARN, "missing — API keys not configured")

# ── 13. Synthetic dataset ─────────────────────────────────────
section("13. SYNTHETIC DATASET")
try:
    with open(DATA / "synthetic_dataset.json") as f:
        ds = json.load(f)
    total_ds = len(ds)
    check("total cases >= 100", PASS if total_ds >= 100 else FAIL, str(total_ds))
    from collections import Counter
    sev_ds = Counter(c.get("expected_severity","?") for c in ds)
    for s in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        check(f"dataset has {s}", PASS if sev_ds.get(s,0) > 0 else FAIL,
              f"{sev_ds.get(s,0)} cases")
    # Check structure of first case
    first = ds[0]
    for field in ["case_id","expected_severity","patient_data"]:
        check(f"dataset field: {field}", PASS if field in first else FAIL)
except Exception as e:
    check("synthetic_dataset.json", FAIL, str(e))

# ── 14. Determinism proof ─────────────────────────────────────
section("14. DETERMINISM PROOF")
try:
    with open(DATA / "determinism_proof.json") as f:
        dp = json.load(f)
    runs = dp.get("runs", [])
    check("3 runs recorded", PASS if len(runs) >= 3 else WARN, str(len(runs)))
    if len(runs) >= 2:
        tokens = [r.get("original_tokens") for r in runs]
        comp = [r.get("compressed_tokens") for r in runs]
        check("identical original_tokens across runs",
              PASS if len(set(tokens)) == 1 else FAIL, str(tokens))
        check("identical compressed_tokens across runs",
              PASS if len(set(comp)) == 1 else FAIL, str(comp))
except Exception as e:
    check("determinism_proof.json", FAIL, str(e))

# ── SUMMARY ───────────────────────────────────────────────────
section("SUMMARY")
passed = sum(1 for r in results if r[0] == PASS)
warned = sum(1 for r in results if r[0] == WARN)
failed = sum(1 for r in results if r[0] == FAIL)
total_checks = len(results)
print(f"\n  Total checks : {total_checks}")
print(f"  ✅ PASS      : {passed}")
print(f"  ⚠️  WARN      : {warned}")
print(f"  ❌ FAIL      : {failed}")
print(f"\n  Score        : {passed}/{total_checks} ({round(passed/total_checks*100)}%)")

if failed:
    print("\n  FAILURES:")
    for s, n, d in results:
        if s == FAIL:
            print(f"    ❌ {n}" + (f" — {d}" if d else ""))
if warned:
    print("\n  WARNINGS:")
    for s, n, d in results:
        if s == WARN:
            print(f"    ⚠️  {n}" + (f" — {d}" if d else ""))
