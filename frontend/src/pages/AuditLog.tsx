import { useState, useEffect, useCallback } from "react";
import { Search, RefreshCw, AlertCircle, X, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { severityConfig, type SeverityLevel } from "@/lib/mock-data";
import { api } from "@/lib/api";

interface AuditEntry {
  id: string;
  timestamp: string;
  patient_id: string;
  patient_name: string;
  severity: SeverityLevel;
  action_taken: string;
  overridden: boolean;
  override_reason?: string;
  performed_by?: string;
}

const POLL_MS = 10_000;

const SPIN_STYLE = `@keyframes queue-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
if (typeof document !== "undefined" && !document.getElementById("queue-spin-style")) {
  const s = document.createElement("style");
  s.id = "queue-spin-style";
  s.textContent = SPIN_STYLE;
  document.head.appendChild(s);
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 py-2.5 border-b last:border-0">
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">{label}</span>
      <span className="text-sm font-medium break-words leading-snug">{value}</span>
    </div>
  );
}

const AuditLog = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [selected, setSelected] = useState<AuditEntry | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [clearing, setClearing] = useState(false);

  const fetchAudit = useCallback(async (manual = false) => {
    if (manual) setSpinning(true);
    try {
      const data = await api.getAuditLog(200);
      setEntries(data.entries || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load audit log");
    } finally {
      setLoading(false);
      if (manual) setTimeout(() => setSpinning(false), 800);
    }
  }, []);

  useEffect(() => {
    fetchAudit();
    const t = setInterval(() => fetchAudit(), POLL_MS);
    return () => clearInterval(t);
  }, [fetchAudit]);

  const handleClearLogs = async () => {
    setClearing(true);
    try {
      await api.clearAuditLog();
      setEntries([]);
      setClearConfirm(false);
    } catch (err: any) {
      setError(err.message || "Failed to clear audit log");
    } finally {
      setClearing(false);
    }
  };

  const filtered = entries.filter((e) => {
    const q = filter.toLowerCase();
    return (
      e.patient_name.toLowerCase().includes(q) ||
      e.patient_id.toLowerCase().includes(q) ||
      e.severity.includes(q) ||
      e.action_taken.toLowerCase().includes(q) ||
      (e.performed_by ?? "").toLowerCase().includes(q)
    );
  });

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      const date = d.toLocaleDateString("en-CA");
      const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
      return `${date} ${time}`;
    } catch {
      return iso;
    }
  };

  const formatFull = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("en-US", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const selectedSev = selected
    ? (severityConfig[(selected.severity || "medium") as SeverityLevel] ?? severityConfig["medium"])
    : null;

  return (
    <main className="container py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold">Audit Log</h1>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <button
            onClick={() => setClearConfirm(true)}
            title="Clear Logs"
            disabled={entries.length === 0}
            className="flex items-center gap-1.5 px-3 h-9 rounded-md text-xs font-medium border border-red-200 text-red-500 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear Logs
          </button>
          <button
            onClick={() => fetchAudit(true)}
            title="Refresh"
            className="flex items-center justify-center h-10 w-10 rounded-full hover:bg-accent"
          >
            <RefreshCw
              className="h-4 w-4"
              style={spinning ? { animation: "queue-spin 0.7s linear infinite" } : {}}
            />
          </button>
          {!loading && (
            <span>{filtered.length} {filtered.length === 1 ? "entry" : "entries"}</span>
          )}
        </div>
      </div>

      <div className="relative mb-6 max-w-md">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by patient, severity, or action..."
          className="h-12 pl-10 text-base"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {error && (
        <Card className="border-red-600 bg-red-50 dark:bg-red-950 mb-6">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <div>
                <p className="font-bold text-red-600">Failed to load audit log</p>
                <p className="text-sm text-red-600">{error}</p>
                <Button onClick={() => fetchAudit(true)} variant="outline" size="sm" className="mt-2">
                  Retry
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="rounded-lg border overflow-x-auto">
        <Table className="min-w-[640px]">
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Patient ID</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Action Taken</TableHead>
              <TableHead>By</TableHead>
              <TableHead>Overridden</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  Loading audit log...
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  {filter
                    ? "No matching entries found."
                    : "No audit entries yet. Triage a patient to see entries here."}
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((entry) => {
                const sevKey = (entry.severity || "medium") as SeverityLevel;
                const sev = severityConfig[sevKey] ?? severityConfig["medium"];
                return (
                  <TableRow
                    key={entry.id}
                    className="cursor-pointer hover:bg-muted/40 transition-colors"
                    onClick={() => setSelected(entry)}
                  >
                    <TableCell className="whitespace-nowrap font-mono text-sm">
                      {formatTimestamp(entry.timestamp)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {entry.patient_id.slice(0, 8).toUpperCase()}
                    </TableCell>
                    <TableCell className="font-medium">{entry.patient_name}</TableCell>
                    <TableCell>
                      <span className={`inline-flex rounded-md px-2.5 py-1 text-xs font-bold ${sev.className}`}>
                        {sev.label}
                      </span>
                    </TableCell>
                    <TableCell className="max-w-xs">{entry.action_taken}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {entry.performed_by || "—"}
                    </TableCell>
                    <TableCell>
                      {entry.overridden ? (
                        <Badge variant="outline" className="border-orange-500 text-orange-500 font-bold">
                          YES
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">No</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Detail dialog */}
      <DialogPrimitive.Root open={!!selected} onOpenChange={(open) => { if (!open) setSelected(null); }}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-lg sm:max-w-xl rounded-xl p-0 overflow-hidden shadow-lg bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
            {selected && selectedSev && (
              <>
                {/* Header strip with inline close button */}
                <div className={`flex items-start justify-between px-6 py-4 ${selectedSev.className}`}>
                  <div className="flex-1 min-w-0">
                    <DialogPrimitive.Title className="flex items-center gap-3 text-base sm:text-lg font-bold">
                      <span className="inline-flex rounded-md px-2.5 py-1 text-xs font-black bg-white/20">
                        {selectedSev.label}
                      </span>
                      <span className="truncate">{selected.patient_name}</span>
                    </DialogPrimitive.Title>
                    <p className="text-xs mt-1 opacity-80 font-mono">
                      {selected.patient_id.toUpperCase()}
                    </p>
                  </div>
                  <DialogPrimitive.Close className="ml-4 mt-0.5 flex-shrink-0 flex items-center justify-center h-7 w-7 rounded-md bg-white/20 hover:bg-white/40 transition-colors">
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                  </DialogPrimitive.Close>
                </div>

                {/* Body */}
                <div className="px-6 py-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
                    <DetailRow label="Timestamp" value={formatFull(selected.timestamp)} />
                    <DetailRow label="Performed By" value={selected.performed_by || "—"} />
                    <DetailRow label="Severity" value={
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-bold ${selectedSev.className}`}>
                        {selectedSev.label}
                      </span>
                    } />
                    <DetailRow label="Overridden" value={
                      selected.overridden ? (
                        <Badge variant="outline" className="border-orange-500 text-orange-500 font-bold text-xs">
                          YES
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">No</span>
                      )
                    } />
                  </div>
                  <DetailRow label="Action Taken" value={selected.action_taken} />
                  {selected.overridden && selected.override_reason && (
                    <DetailRow label="Override Reason" value={selected.override_reason} />
                  )}
                </div>
              </>
            )}
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
      {/* Clear Logs confirmation dialog */}
      <DialogPrimitive.Root open={clearConfirm} onOpenChange={(open) => { if (!open) setClearConfirm(false); }}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-sm rounded-xl p-6 shadow-lg bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-full bg-red-100 dark:bg-red-950 flex-shrink-0">
                <Trash2 className="h-5 w-5 text-red-500" />
              </div>
              <DialogPrimitive.Title className="text-base font-bold">Clear Audit Log?</DialogPrimitive.Title>
            </div>
            <p className="text-sm text-muted-foreground mb-5">
              This will permanently delete all {entries.length} audit {entries.length === 1 ? "entry" : "entries"}. This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setClearConfirm(false)} disabled={clearing}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-red-500 hover:bg-red-600 text-white"
                onClick={handleClearLogs}
                disabled={clearing}
              >
                {clearing ? "Clearing..." : "Clear All Logs"}
              </Button>
            </div>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </main>
  );
};

export default AuditLog;
