import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpDown, Clock, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { severityConfig, type SeverityLevel } from "@/lib/mock-data";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";

interface QueuePatient {
  id: string;
  name: string;
  age: number;
  chiefComplaint: string;
  severity: SeverityLevel;
  arrivalTime: string;
  waitTime: number; // in minutes
  status: "waiting" | "in-progress" | "completed";
}

const mockQueue: QueuePatient[] = [
  {
    id: "P-4501",
    name: "John Martinez",
    age: 45,
    chiefComplaint: "Chest pain",
    severity: "critical",
    arrivalTime: "08:15",
    waitTime: 5,
    status: "in-progress",
  },
  {
    id: "P-4502",
    name: "Sarah Johnson",
    age: 32,
    chiefComplaint: "Severe headache",
    severity: "high",
    arrivalTime: "08:22",
    waitTime: 12,
    status: "waiting",
  },
  {
    id: "P-4503",
    name: "Michael Chen",
    age: 28,
    chiefComplaint: "Ankle injury",
    severity: "medium",
    arrivalTime: "08:30",
    waitTime: 20,
    status: "waiting",
  },
  {
    id: "P-4504",
    name: "Emily Davis",
    age: 55,
    chiefComplaint: "Difficulty breathing",
    severity: "critical",
    arrivalTime: "08:35",
    waitTime: 15,
    status: "waiting",
  },
  {
    id: "P-4505",
    name: "Robert Wilson",
    age: 67,
    chiefComplaint: "Abdominal pain",
    severity: "high",
    arrivalTime: "08:40",
    waitTime: 20,
    status: "waiting",
  },
  {
    id: "P-4506",
    name: "Lisa Anderson",
    age: 24,
    chiefComplaint: "Minor cut",
    severity: "low",
    arrivalTime: "08:45",
    waitTime: 25,
    status: "waiting",
  },
  {
    id: "P-4507",
    name: "David Brown",
    age: 41,
    chiefComplaint: "Fever and cough",
    severity: "medium",
    arrivalTime: "08:50",
    waitTime: 30,
    status: "waiting",
  },
  {
    id: "P-4508",
    name: "Jennifer Lee",
    age: 19,
    chiefComplaint: "Sprained wrist",
    severity: "low",
    arrivalTime: "08:55",
    waitTime: 35,
    status: "waiting",
  },
];

type SortBy = "severity" | "arrival" | "waitTime";

const Queue = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [sortBy, setSortBy] = useState<SortBy>("severity");
  const [patients, setPatients] = useState<QueuePatient[]>(mockQueue);

  const canStartTriage = hasPermission(user?.role, "canStartTriage");

  const severityOrder: Record<SeverityLevel, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
  };

  const sortPatients = (criteria: SortBy) => {
    const sorted = [...patients].sort((a, b) => {
      if (criteria === "severity") {
        return severityOrder[a.severity] - severityOrder[b.severity];
      } else if (criteria === "arrival") {
        return a.arrivalTime.localeCompare(b.arrivalTime);
      } else {
        return a.waitTime - b.waitTime;
      }
    });
    setPatients(sorted);
    setSortBy(criteria);
  };

  const getStatusBadge = (status: QueuePatient["status"]) => {
    const variants = {
      waiting: "outline",
      "in-progress": "default",
      completed: "secondary",
    } as const;

    const labels = {
      waiting: "Waiting",
      "in-progress": "In Progress",
      completed: "Completed",
    };

    return (
      <Badge variant={variants[status]} className="font-medium">
        {labels[status]}
      </Badge>
    );
  };

  const criticalCount = patients.filter((p) => p.severity === "critical" && p.status === "waiting").length;
  const highCount = patients.filter((p) => p.severity === "high" && p.status === "waiting").length;
  const totalWaiting = patients.filter((p) => p.status === "waiting").length;

  return (
    <main id="main-content" className="container max-w-6xl py-8 space-y-6" role="main">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Patient Queue</h1>
          <p className="text-muted-foreground mt-1">
            {totalWaiting} patients waiting • {criticalCount} critical • {highCount} high priority
          </p>
        </div>
        <Button onClick={() => navigate("/")} size="lg" className="h-12 text-base">
          New Patient Intake
        </Button>
      </div>

      {/* Alert for Critical Patients */}
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

      {/* Sort Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Sort Queue By</CardTitle>
            <div className="flex items-center gap-2">
              <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
              <Select value={sortBy} onValueChange={(value) => sortPatients(value as SortBy)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="severity">Severity (Critical First)</SelectItem>
                  <SelectItem value="arrival">Arrival Time (Earliest)</SelectItem>
                  <SelectItem value="waitTime">Wait Time (Longest)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Patient Queue List */}
      <div className="space-y-3">
        {patients.map((patient) => {
          const sev = severityConfig[patient.severity];
          return (
            <Card
              key={patient.id}
              className={`cursor-pointer ${
                patient.status === "in-progress" ? "border-primary" : ""
              }`}
              onClick={() => {
                // In real app: navigate to patient details
                console.log("View patient:", patient.id);
              }}
            >
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4">
                  {/* Patient Info */}
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex flex-col items-center min-w-[80px]">
                      <span
                        className={`inline-flex items-center rounded-md px-3 py-1 text-sm font-bold ${sev.className}`}
                      >
                        {sev.label}
                      </span>
                      <span className="text-xs text-muted-foreground mt-1">{patient.id}</span>
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-bold">{patient.name}</h3>
                        {getStatusBadge(patient.status)}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Age {patient.age} • {patient.chiefComplaint}
                      </p>
                    </div>
                  </div>

                  {/* Time Info */}
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-center">
                      <p className="text-muted-foreground">Arrival</p>
                      <p className="font-bold">{patient.arrivalTime}</p>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center gap-1 justify-center">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <p className="text-muted-foreground">Wait</p>
                      </div>
                      <p
                        className={`font-bold ${
                          patient.waitTime > 30
                            ? "text-red-600"
                            : patient.waitTime > 15
                            ? "text-orange-600"
                            : ""
                        }`}
                      >
                        {patient.waitTime} min
                      </p>
                    </div>
                  </div>

                  {/* Action Button - Only for medical staff */}
                  {canStartTriage && (
                    <Button
                      variant={patient.severity === "critical" ? "destructive" : "default"}
                      size="lg"
                      className="h-14 px-8 text-lg font-bold"
                      onClick={(e) => {
                        e.stopPropagation();
                        // In real app: start triage for this patient
                        console.log("Start triage for:", patient.id);
                      }}
                      aria-label={`${patient.status === "in-progress" ? "Continue" : "Start"} triage for ${patient.name}, ${patient.severity} severity`}
                    >
                      {patient.status === "in-progress" ? "Continue" : "Start Triage"}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {patients.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center">
            <p className="text-lg text-muted-foreground">No patients in queue</p>
          </CardContent>
        </Card>
      )}
    </main>
  );
};

export default Queue;
