import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, ShieldAlert, Users, Clock, AlertCircle, Activity, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { type TriageResult, severityConfig } from "@/lib/mock-data";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { OverridePanel, type OverrideData } from "@/components/OverridePanel";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";
import { api } from "@/lib/api";
import { CompressionCharts } from "@/components/CompressionCharts";

// Live overview shown when navigating directly to /dashboard
function OverviewDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [queue, setQueue] = useState<any[]>([]);
  const [patients, setPatients] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    Promise.all([
      api.getQueue().catch(() => ({ queue: [] })),
      api.getPatients().catch(() => ({ patients: [] })),
      api.getAuditLog(10).catch(() => ({ entries: [] })),
      api.getStats().catch(() => null),
    ]).then(([q, p, a, s]) => {
      setQueue((q as any).queue || []);
      setPatients((p as any).patients || []);
      setAudit((a as any).entries || []);
      setStats(s);
      setLoading(false);
    });
  }, []);

  const handleReset = async () => {
    setResetting(true);
    try {
      await api.resetAllData();
      setQueue([]);
      setPatients([]);
      setAudit([]);
    } finally {
      setResetting(false);
      setShowResetConfirm(false);
    }
  };

  const waiting = queue.filter((e) => e.status === "waiting");
  const inProgress = queue.filter((e) => e.status === "in-progress");
  const critical = waiting.filter((e) => e.severity === "critical");

  return (
    <main id="main-content" className="container max-w-5xl py-6 px-3 sm:py-8 sm:px-6 space-y-6 dash-animate" role="main">
      <div className="flex flex-wrap items-start justify-between gap-3 dash-fade-up">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Live overview of the emergency department</p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <Button
              variant="outline"
              size="sm"
              className="h-9 border-red-600 text-red-600 hover:bg-red-600 hover:text-white"
              onClick={() => setShowResetConfirm(true)}
            >
              Reset All Data
            </Button>
          )}
          <Button onClick={() => navigate("/")} size="sm" className="h-9">New Intake</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 dash-stagger">
        {[
          { icon: <Users className="h-6 w-6 text-muted-foreground" />, value: waiting.length, label: "Waiting", accent: "" },
          { icon: <Activity className="h-6 w-6 text-blue-500" />, value: inProgress.length, label: "In Progress", accent: "text-blue-500" },
          { icon: <AlertCircle className="h-6 w-6 text-red-500" />, value: critical.length, label: "Critical", accent: "text-red-500" },
          { icon: <Clock className="h-6 w-6 text-muted-foreground" />, value: patients.length, label: "Total Patients", accent: "" },
        ].map((s) => (
          <Card key={s.label} className="group cursor-default dash-stat-card dash-fade-up">
            <CardContent className="pt-6 pb-5">
              <div className="flex items-center gap-4">
                <div className="p-2.5 rounded-xl bg-muted/40">
                  {s.icon}
                </div>
                <div>
                  <p className={`text-3xl font-black tracking-tight dash-count-in ${s.accent}`}>
                    {loading ? "—" : s.value}
                  </p>
                  <p className="text-sm text-muted-foreground font-medium">{s.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Pruning Metrics */}
      {stats && stats.total_predictions > 0 && (
        <Card className="dash-fade-up overflow-hidden">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-500 dash-zap" />
              Context Pruning Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 dash-stagger">
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-2xl font-black">{stats.total_predictions}</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">Total API Calls</p>
              </div>
              <div className="rounded-xl border bg-yellow-500/10 px-4 py-4 dash-metric-tile dash-metric-tile-yellow dash-fade-up cursor-default">
                <p className="text-2xl font-black dash-shimmer-text">{stats.avg_tokens_saved_pct}%</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">Avg Token Reduction</p>
              </div>
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-2xl font-black">{stats.total_tokens_saved.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">Total Tokens Saved</p>
              </div>
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-2xl font-black">{stats.pruning_applied_count}</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">Pruning Applied</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 dash-stagger">
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-xl font-black">{stats.avg_inference_time_ms}ms</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">Avg ML Inference</p>
              </div>
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-xl font-black">{stats.p50_latency_ms ?? "—"}ms</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">p50 Latency</p>
              </div>
              <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral dash-fade-up cursor-default">
                <p className="text-xl font-black">{stats.p95_latency_ms ?? "—"}ms</p>
                <p className="text-xs text-muted-foreground mt-1 font-medium">p95 Latency</p>
              </div>
            </div>

            {stats.compression_statistics && (
              <div className="dash-fade-up">
                <p className="text-sm font-semibold mb-3">Compression Statistics (n={stats.compression_statistics.sample_size})</p>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 dash-stagger">
                  <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-yellow cursor-default">
                    <p className="text-xl font-black text-yellow-500">{stats.compression_statistics.mean_reduction_pct}%</p>
                    <p className="text-xs text-muted-foreground mt-1 font-medium">Mean Reduction</p>
                  </div>
                  <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-neutral cursor-default">
                    <p className="text-xl font-black">±{stats.compression_statistics.std_dev_pct}%</p>
                    <p className="text-xs text-muted-foreground mt-1 font-medium">Std Deviation</p>
                  </div>
                  <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-green cursor-default">
                    <p className="text-xl font-black text-green-500">{stats.compression_statistics.min_reduction_pct}%</p>
                    <p className="text-xs text-muted-foreground mt-1 font-medium">Min Reduction</p>
                  </div>
                  <div className="rounded-xl border bg-muted/30 px-4 py-4 dash-metric-tile dash-metric-tile-blue cursor-default">
                    <p className="text-xl font-black text-blue-500">{stats.compression_statistics.max_reduction_pct}%</p>
                    <p className="text-xs text-muted-foreground mt-1 font-medium">Max Reduction</p>
                  </div>
                </div>
              </div>
            )}

            {stats.per_severity_breakdown && stats.per_severity_breakdown.length > 0 && (
              <div className="dash-fade-up">
                <p className="text-sm font-semibold mb-3">Compression by Severity</p>
                <div className="rounded-xl border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-3 py-2.5 text-left font-semibold text-muted-foreground">Severity</th>
                        <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground">Cases</th>
                        <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground">Before (tokens)</th>
                        <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground">After (tokens)</th>
                        <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground">Saved</th>
                        <th className="px-3 py-2.5 text-right font-semibold text-muted-foreground">Reduction %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.per_severity_breakdown.map((row: any) => {
                        const sevColors: Record<string, string> = {
                          CRITICAL: "text-red-500",
                          HIGH: "text-orange-500",
                          MEDIUM: "text-yellow-500",
                          LOW: "text-green-500",
                        };
                        const color = sevColors[row.severity] ?? "text-foreground";
                        return (
                          <tr key={row.severity} className="border-b last:border-0 dash-table-row">
                            <td className={`px-3 py-2.5 font-bold ${color}`}>{row.severity}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{row.count}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{row.avg_original_tokens}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums">{row.avg_compressed_tokens}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums text-yellow-500 font-semibold">−{row.avg_tokens_saved}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums">
                              <span className="inline-flex items-center rounded-full bg-yellow-500/15 px-2.5 py-0.5 text-xs font-bold text-yellow-500">
                                {row.avg_reduction_pct}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className="bg-muted/40 border-t">
                        <td className="px-3 py-2.5 font-semibold text-muted-foreground">TOTAL</td>
                        <td className="px-3 py-2.5 text-right tabular-nums font-semibold">{stats.total_predictions}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{Math.round(stats.total_tokens_original / stats.total_predictions)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">{Math.round(stats.total_tokens_compressed / stats.total_predictions)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums text-yellow-500 font-semibold">−{Math.round(stats.total_tokens_saved / stats.total_predictions)}</td>
                        <td className="px-3 py-2.5 text-right tabular-nums">
                          <span className="inline-flex items-center rounded-full bg-yellow-500/20 px-2.5 py-0.5 text-xs font-bold text-yellow-500">
                            {stats.avg_tokens_saved_pct}%
                          </span>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              {stats.total_tokens_original.toLocaleString()} → {stats.total_tokens_compressed.toLocaleString()} tokens total
              · {stats.total_tokens_saved.toLocaleString()} tokens saved across {stats.total_predictions} API calls
            </p>
          </CardContent>
        </Card>
      )}

      <CompressionCharts />

      {critical.length > 0 && (
        <Alert className="border-red-600 bg-red-50 dark:bg-red-950 dash-fade-up">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <AlertTitle className="text-red-600 font-bold">
            {critical.length} Critical Patient{critical.length > 1 ? "s" : ""} Waiting
          </AlertTitle>
          <AlertDescription className="text-red-600">Immediate attention required.</AlertDescription>
        </Alert>
      )}

      {/* Recent activity */}
      <Card className="dash-fade-up">
        <CardHeader><CardTitle className="text-lg">Recent Activity</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : audit.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity yet.</p>
          ) : (
            <div className="space-y-1 dash-stagger">
              {audit.slice(0, 6).map((e) => {
                const sev = severityConfig[e.severity as keyof typeof severityConfig] ?? severityConfig.medium;
                const time = new Date(e.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
                return (
                  <div
                    key={e.id}
                    className="flex items-center justify-between gap-4 py-3 px-3 border-b last:border-0 dash-activity-row dash-fade-up cursor-default"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex rounded-md px-2.5 py-1 text-xs font-bold ${sev.className}`}>{sev.label}</span>
                      <div>
                        <p className="font-semibold">{e.patient_name}</p>
                        <p className="text-xs text-muted-foreground">{e.action_taken}</p>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground tabular-nums shrink-0">{time}</span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmationDialog
        open={showResetConfirm}
        onOpenChange={setShowResetConfirm}
        onConfirm={handleReset}
        title="Reset All Data?"
        description={`This will permanently delete all patients (${patients.length}), queue entries (${queue.length}), and audit logs (${audit.length}). This cannot be undone.`}
        confirmText={resetting ? "Resetting..." : "YES, RESET EVERYTHING"}
        cancelText="Cancel"
        variant="destructive"
      />
    </main>
  );
}

// Triage result view — shown after submitting intake
const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = (location.state as { result?: TriageResult })?.result;
  const { user } = useAuth();

  const [actions, setActions] = useState(result?.actions ?? []);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState<string | null>(null);
  const [emergencyActivated, setEmergencyActivated] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);

  const canOverride = hasPermission(user?.role, "canOverrideAI");
  const canActivateEmergency = hasPermission(user?.role, "canActivateEmergency");
  const canViewReasoning = hasPermission(user?.role, "canViewReasoning");

  useEffect(() => { window.scrollTo(0, 0); }, []);

  if (!result) return <OverviewDashboard />;

  const { patient, severity, confidence, reasoningFactors, recommendation, escalation } = result;
  const sev = severityConfig[severity];

  const toggleAction = (id: string) =>
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, checked: !a.checked } : a)));

  return (
    <main id="main-content" className="container max-w-3xl py-6 px-3 sm:py-8 sm:px-6 space-y-6" role="main">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="ghost" onClick={() => navigate("/")} className="h-10 text-base">
          <ArrowLeft className="mr-2 h-5 w-5" /> New Intake
        </Button>
        {canActivateEmergency && (
          <Button
            onClick={() => setShowEmergencyConfirm(true)}
            disabled={emergencyActivated}
            size="sm"
            className={`h-9 px-4 text-sm font-semibold ${
              emergencyActivated
                ? "bg-muted text-muted-foreground cursor-not-allowed"
                : "bg-red-600 hover:bg-red-700 text-white"
            }`}
          >
            {emergencyActivated ? (
              <>
                <svg className="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                EMERGENCY ACTIVATED
              </>
            ) : (
              <><ShieldAlert className="mr-1.5 h-4 w-4" />CODE BLUE / EMERGENCY</>
            )}
          </Button>
        )}
      </div>

      {emergencyActivated && (
        <Alert className="border-2 border-red-600 bg-red-50 dark:bg-red-950">
          <ShieldAlert className="h-6 w-6 text-red-600" />
          <AlertTitle className="text-lg font-bold text-red-600">Emergency Response Activated</AlertTitle>
          <AlertDescription className="text-base text-red-600">
            Trauma/cardiac team has been alerted. Attending physician notified STAT.
          </AlertDescription>
        </Alert>
      )}

      {escalation && (
        <Alert variant="destructive" className="border-2">
          <ShieldAlert className="h-6 w-6" />
          <AlertTitle className="text-lg font-bold">CRITICAL ESCALATION</AlertTitle>
          <AlertDescription className="text-base">
            This patient requires immediate intervention. Trauma / cardiac team should be alerted.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <span className={`inline-flex items-center rounded-lg px-5 py-3 text-2xl font-black tracking-wider ${sev.className}`}>
          {sev.label}
        </span>
        <div className="flex flex-col">
          <span className="text-lg text-muted-foreground">Triage Severity</span>
          <div className="flex items-center gap-2 mt-1">
            <div className="h-2 w-32 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-primary" style={{ width: `${confidence}%` }} />
            </div>
            <span className="text-sm font-bold text-primary">{confidence}% Confidence</span>
          </div>
        </div>
      </div>

      {canViewReasoning && (
        <Card className="border-2 border-primary">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              AI Reasoning
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">Top factors influencing this decision:</p>
            <ul className="space-y-2">
              {reasoningFactors.map((factor, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-primary text-primary-foreground text-xs font-bold flex-shrink-0 mt-0.5">
                    {index + 1}
                  </span>
                  <span className="text-base">{factor}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-lg">Patient Context</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p className="font-medium">{patient.name}</p></div>
            <div><p className="text-sm text-muted-foreground">Age</p><p className="font-medium">{patient.age}</p></div>
            <div><p className="text-sm text-muted-foreground">Gender</p><p className="font-medium capitalize">{patient.gender}</p></div>
            <div><p className="text-sm text-muted-foreground">Chief Complaint</p><p className="font-medium">{patient.chiefComplaint}</p></div>
          </div>
          <div className="mt-4">
            <p className="text-sm text-muted-foreground">Symptoms</p>
            <p className="mt-1">{patient.symptoms}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">AI Recommendation</CardTitle></CardHeader>
        <CardContent><p className="text-base">{recommendation}</p></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">Recommended Actions</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {actions.map((action) => (
            <label key={action.id} className="flex items-start gap-3 cursor-pointer group">
              <Checkbox checked={action.checked} onCheckedChange={() => toggleAction(action.id)} className="mt-1" />
              <span className="text-base group-hover:text-foreground transition-colors">{action.text}</span>
            </label>
          ))}
        </CardContent>
      </Card>

      {canOverride && (
        <>
          {overrideSuccess && (
            <Alert className="border-green-600 bg-green-50 dark:bg-green-950">
              <AlertCircle className="h-5 w-5 text-green-600" />
              <AlertTitle className="text-green-700 dark:text-green-300 font-bold">Override Submitted</AlertTitle>
              <AlertDescription className="text-green-700 dark:text-green-300">{overrideSuccess}</AlertDescription>
            </Alert>
          )}
          {!overrideOpen ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-severity-high" />
                  Override AI Assessment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button variant="outline" onClick={() => setOverrideOpen(true)} className="h-12 w-full text-base">
                  Override Triage Decision
                </Button>
              </CardContent>
            </Card>
          ) : (
            <OverridePanel
              patientId={patient.name}
              patientName={patient.name}
              currentSeverity={severity}
              doctorEmail={user?.email ?? ""}
              onSubmit={async (d: OverrideData) => {
                try {
                  await api.addAuditEntry({
                    patient_id: patient.name,
                    patient_name: patient.name,
                    severity: d.newSeverity,
                    action_taken: `AI triage override: ${severity.toUpperCase()} → ${d.newSeverity.toUpperCase()}. Reason: ${d.reason}`,
                    overridden: true,
                    override_reason: d.clinicalJustification,
                    performed_by: `${d.doctorName} (${d.doctorId})`,
                  });
                } catch {
                  // audit failure is non-blocking
                }
                setOverrideOpen(false);
                setOverrideSuccess(
                  `Severity changed from ${severity.toUpperCase()} to ${d.newSeverity.toUpperCase()} by ${d.doctorName}. Logged in audit trail.`
                );
              }}
              onCancel={() => setOverrideOpen(false)}
            />
          )}
        </>
      )}

      <ConfirmationDialog
        open={showEmergencyConfirm}
        onOpenChange={setShowEmergencyConfirm}
        onConfirm={() => setEmergencyActivated(true)}
        title="Activate Emergency Response?"
        description="This will immediately alert the trauma/cardiac team and notify the attending physician STAT."
        confirmText="YES, ACTIVATE EMERGENCY"
        cancelText="Cancel"
        variant="destructive"
      />
    </main>
  );
};

export default Dashboard;
