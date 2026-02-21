import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { mockAuditLog, severityConfig } from "@/lib/mock-data";

const AuditLog = () => {
  const [filter, setFilter] = useState("");

  const filtered = mockAuditLog.filter((entry) => {
    const q = filter.toLowerCase();
    return (
      entry.patientName.toLowerCase().includes(q) ||
      entry.patientId.toLowerCase().includes(q) ||
      entry.severity.includes(q) ||
      entry.actionTaken.toLowerCase().includes(q)
    );
  });

  return (
    <main className="container py-8">
      <h1 className="mb-6 text-3xl font-bold">Audit Log</h1>

      {/* Search */}
      <div className="relative mb-6 max-w-md">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by patient, severity, or action..."
          className="h-12 pl-10 text-base"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-base">Timestamp</TableHead>
              <TableHead className="text-base">Patient ID</TableHead>
              <TableHead className="text-base">Patient</TableHead>
              <TableHead className="text-base">Severity</TableHead>
              <TableHead className="text-base">Action Taken</TableHead>
              <TableHead className="text-base">Overridden</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((entry) => {
              const sev = severityConfig[entry.severity];
              return (
                <TableRow key={entry.id}>
                  <TableCell className="whitespace-nowrap font-mono text-sm">{entry.timestamp}</TableCell>
                  <TableCell className="font-mono text-sm">{entry.patientId}</TableCell>
                  <TableCell className="font-medium">{entry.patientName}</TableCell>
                  <TableCell>
                    <span className={`inline-flex rounded-md px-2.5 py-1 text-xs font-bold ${sev.className}`}>
                      {sev.label}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-xs">{entry.actionTaken}</TableCell>
                  <TableCell>
                    {entry.overridden ? (
                      <Badge variant="outline" className="border-severity-high text-severity-high font-bold">YES</Badge>
                    ) : (
                      <span className="text-muted-foreground">No</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  No matching entries found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </main>
  );
};

export default AuditLog;
