import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpDown, Clock, AlertCircle, RefreshCw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { severityConfig, type SeverityLevel } from "@/lib/mock-data";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";
import { api } from "@/lib/api";
import { OverridePanel, type OverrideData } from "@/components/OverridePanel";

// Inject spin keyframe once
const SPIN_STYLE = `@keyframes queue-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
if (typeof document !== "undefined" && !document.getElementById("queue-spin-style")) {
  const s = document.createElement("style");
  s.id = "queue-spin-style";
  s.textContent = SPIN_STYLE;
  document.head.appendChild(s);
}

interface QueuePatient {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  chief_complaint: string;
  severity: SeverityLevel;
  priority: number;
  status: "waiting" | "in-progress" | "completed";
  added_at: string;
}

type SortBy = "severity" | "arrival" | "waitTime";
const POLL_MS = 5_000;
const severityOrder: Record<SeverityLevel, number> = { critical: 0, high: 1, medium: 2, low: 3 };

function liveWait(added_at: string, now: number) {
  const mins = Math.max(0, Math.floor((now - new Date(added_at).getTime()) / 60_000));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return { mins, display: h > 0 ? `${h}h ${m}m` : `${m} min` };
}

const OVERRIDE_LOGGED_KEY = "queue_override_logged_ids";

function getOverrideLoggedIds(): Set<string> {
  try {
    const raw = sessionStorage.getItem(OVERRIDE_LOGGED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch { return new Set(); }
}

function addOverrideLoggedId(id: string) {
  const ids = getOverrideLoggedIds();
  ids.add(id);
  sessionStorage.setItem(OVERRIDE_LOGGED_KEY, JSON.stringify([...ids]));
}

const Queue = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canStartTriage = hasPermission(user?.role, "canStartTriage");
  const canOverride = hasPermission(user?.role, "canOverrideAI");

  const [patients, setPatients] = useState<QueuePatient[]>([]);
  const [sortBy, setSortBy] = useState<SortBy>("severity");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [overridingPatientId, setOverridingPatientId] = useState<string | null>(null);
  // Persisted in sessionStorage so tab switches don't clear it
  const [overrideLoggedIds, setOverrideLoggedIds] = useState<Set<string>>(() => getOverrideLoggedIds());

  // Sync overrideLoggedIds from sessionStorage when tab becomes visible again
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        setOverrideLoggedIds(getOverrideLoggedIds());
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, []);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(t);
  }, []);

  const sortList = useCallback((list: QueuePatient[], by: SortBy) =>
    [...list].sort((a, b) => {
      if (by === "severity") return severityOrder[a.severity] - severityOrder[b.severity];
      if (by === "arrival") return a.added_at.localeCompare(b.added_at);
      return new Date(a.added_at).getTime() - new Date(b.added_at).getTime();
    }), []);

  const fetchQueue = useCallback(async (manual = false) => {
    if (manual) setSpinning(true);
    try {
      const data = await api.getQueue();
      const items: QueuePatient[] = (data.queue || [])
        .filter((e: any) => e.status !== "completed")
        .map((e: any) => ({
          id: e.id,
          patient_id: e.patient_id,
          name: e.name || "Unknown",
          age: e.age || 0,
          chief_complaint: e.chief_complaint || "N/A",
          severity: (e.severity || "medium") as SeverityLevel,
          priority: e.priority ?? 2,
          status: e.status || "waiting",
          added_at: e.added_at,
        }));
      setPatients(prev => sortList(items, sortBy));
      setError(null);
    } catch (err: any) {
      const msg = err.message || "Failed to load queue";
      setError(msg.includes("timeout") ? "Backend not reachable — is the server running?" : msg);
    } finally {
      setLoading(false);
      if (manual) setTimeout(() => setSpinning(false), 1200);
    }
  }, [sortBy, sortList]);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(() => fetchQueue(), POLL_MS);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const handleSort = (by: SortBy) => {
    setSortBy(by);
    setPatients(prev => sortList(prev, by));
  };

  const handleStatusToggle = async (patient: QueuePatient) => {
    const next = patient.status === "waiting" ? "in-progress" : "completed";
    setUpdatingId(patient.id);
    try {
      await api.updateQueueStatus(patient.id, next);
      if (next === "completed") {
        setPatients(prev => prev.filter(p => p.id !== patient.id));
      } else {
        setPatients(prev => prev.map(p => p.id === patient.id ? { ...p, status: next } : p));
      }
    } catch (err: any) {
      setError(err.message || "Failed to update status");
    } finally {
      setUpdatingId(null);
    }
  };

  const criticalCount = patients.filter(p => p.severity === "critical" && p.status === "waiting").length;
  const highCount = patients.filter(p => p.severity === "high" && p.status === "waiting").length;
  const totalWaiting = patients.filter(p => p.status === "waiting").length;

  return (
    <main id="main-content" className="container max-w-6xl py-6 px-3 sm:py-8 sm:px-6 space-y-6" role="main">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold">Patient Queue</h1>
          <p className="text-muted-foreground mt-1">
            {loading ? "Loading..." : error ? "Error loading queue"
              : `${totalWaiting} patients waiting • ${criticalCount} critical • ${highCount} high priority`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Refresh button — ghost style, spins on click */}
          <button
            onClick={() => fetchQueue(true)}
            title="Refresh queue"
            className="flex items-center justify-center h-12 w-12 rounded-full text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <RefreshCw
              className={`h-5 w-5 allow-animation${spinning ? " spinning-icon" : ""}`}
              style={spinning ? { animation: "queue-spin 0.7s linear infinite" } : {}}
            />
          </button>
          <Button onClick={() => navigate("/")} size="lg" className="h-12 text-base">
            Add Patient to Queue
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-600 bg-red-50 dark:bg-red-950">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <div>
                <p className="font-bold text-red-600">Failed to load queue</p>
                <p className="text-sm text-red-600">{error}</p>
                <Button onClick={() => fetchQueue(true)} variant="outline" size="sm" className="mt-2">Retry</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {criticalCount > 0 && (
        <Card className="border-red-600 bg-red-50 dark:bg-red-950">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <div>
                <p className="font-bold text-red-600">
                  {criticalCount} Critical Patient{criticalCount > 1 ? "s" : ""} Waiting
                </p>
                <p className="text-sm text-red-600">Immediate attention required</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <ArrowUpDown className="h-4 w-4" />
        <span>Sort by</span>
        <Select value={sortBy} onValueChange={v => handleSort(v as SortBy)}>
          <SelectTrigger className="h-8 w-[190px] border-0 bg-transparent px-2 text-sm focus:ring-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="severity">Severity (Critical First)</SelectItem>
            <SelectItem value="arrival">Arrival Time (Earliest)</SelectItem>
            <SelectItem value="waitTime">Wait Time (Longest)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-3">
        {patients.map(patient => {
          const sev = severityConfig[patient.severity];
          const isUpdating = updatingId === patient.id;
          const isOverriding = overridingPatientId === patient.id;
          const arrivalTime = new Date(patient.added_at).toLocaleTimeString("en-US", {
            hour: "2-digit", minute: "2-digit",
          });
          const { mins, display: waitDisplay } = liveWait(patient.added_at, now);

          return (
            <div key={patient.id} className="space-y-2">
              <Card className={patient.status === "in-progress" ? "border-primary" : ""}>
                <CardContent className="pt-4 pb-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                    {/* Left: severity + patient info */}
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="flex flex-col items-center shrink-0">
                        <span className={`inline-flex items-center rounded-md px-3 py-1 text-sm font-bold ${sev.className}`}>
                          {sev.label}
                        </span>
                        <span className="text-xs text-muted-foreground mt-1">{patient.patient_id.slice(0, 8)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <h3 className="text-base font-bold">{patient.name}</h3>
                          <Badge variant={patient.status === "in-progress" ? "default" : "outline"} className="font-medium text-xs">
                            {patient.status === "in-progress" ? "In Progress" : "Waiting"}
                          </Badge>
                          {overrideLoggedIds.has(patient.id) && (
                            <Badge variant="outline" className="text-green-600 border-green-600 font-medium text-xs">
                              Override Logged
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground truncate">Age {patient.age} • {patient.chief_complaint}</p>
                      </div>
                    </div>

                    {/* Bottom row on mobile: arrival + wait + button */}
                    <div className="flex items-center justify-between gap-3 sm:gap-6">
                      <div className="flex items-center gap-4 text-sm">
                        <div className="text-center">
                          <p className="text-muted-foreground text-xs">Arrival</p>
                          <p className="font-bold">{arrivalTime}</p>
                        </div>
                        <div className="text-center">
                          <div className="flex items-center gap-1 justify-center">
                            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                            <p className="text-muted-foreground text-xs">Wait</p>
                          </div>
                          <p className={`font-bold tabular-nums ${mins > 30 ? "text-red-600" : mins > 15 ? "text-orange-500" : ""}`}>
                            {waitDisplay}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {canOverride && patient.status === "in-progress" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-10 px-3 text-sm font-semibold border-severity-high text-severity-high hover:bg-severity-high hover:text-white"
                            onClick={() => setOverridingPatientId(isOverriding ? null : patient.id)}
                          >
                            <AlertTriangle className="h-4 w-4 mr-1" />
                            {isOverriding ? "Cancel" : "Override"}
                          </Button>
                        )}
                        {canStartTriage && (
                          <Button
                            variant={patient.severity === "critical" ? "destructive" : "default"}
                            size="sm"
                            className="h-10 px-4 text-sm font-bold"
                            disabled={isUpdating}
                            onClick={() => handleStatusToggle(patient)}
                          >
                            {isUpdating
                              ? <RefreshCw style={{ animation: "queue-spin 0.7s linear infinite" }} className="h-4 w-4 allow-animation" />
                              : patient.status === "in-progress" ? "Complete" : "Start Triage"}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {isOverriding && (
                <OverridePanel
                  patientId={patient.patient_id}
                  patientName={patient.name}
                  currentSeverity={patient.severity}
                  doctorEmail={user?.email ?? ""}
                  onSubmit={async (d: OverrideData) => {
                    try {
                      await api.addAuditEntry({
                        patient_id: patient.patient_id,
                        patient_name: patient.name,
                        severity: d.newSeverity,
                        action_taken: `AI triage override: ${patient.severity.toUpperCase()} → ${d.newSeverity.toUpperCase()}. Reason: ${d.reason}`,
                        overridden: true,
                        override_reason: d.clinicalJustification,
                        performed_by: `${d.doctorName} (${d.doctorId})`,
                      });
                    } catch { /* non-blocking */ }
                    addOverrideLoggedId(patient.id);
                    setOverrideLoggedIds(getOverrideLoggedIds());
                    setOverridingPatientId(null);
                  }}
                  onCancel={() => setOverridingPatientId(null)}
                />
              )}
            </div>
          );
        })}
      </div>

      {!loading && patients.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center">
            <p className="text-lg text-muted-foreground">No patients in queue</p>
            <p className="text-sm text-muted-foreground mt-1">Use "Add Patient to Queue" to register a new patient</p>
          </CardContent>
        </Card>
      )}
    </main>
  );
};

export default Queue;
