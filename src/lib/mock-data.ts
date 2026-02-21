export type SeverityLevel = "critical" | "high" | "medium" | "low";

export interface PatientIntake {
  name: string;
  age: string;
  gender: string;
  chiefComplaint: string;
  symptoms: string;
}

export interface TriageResult {
  patient: PatientIntake;
  severity: SeverityLevel;
  recommendation: string;
  actions: { id: string; text: string; checked: boolean }[];
  escalation: boolean;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  patientId: string;
  patientName: string;
  severity: SeverityLevel;
  actionTaken: string;
  overridden: boolean;
}

export const severityConfig: Record<SeverityLevel, { label: string; className: string }> = {
  critical: { label: "CRITICAL", className: "bg-severity-critical text-severity-critical-foreground" },
  high: { label: "HIGH", className: "bg-severity-high text-severity-high-foreground" },
  medium: { label: "MEDIUM", className: "bg-severity-medium text-severity-medium-foreground" },
  low: { label: "LOW", className: "bg-severity-low text-severity-low-foreground" },
};

export function getMockTriageResult(intake: PatientIntake): TriageResult {
  // Simulate severity based on keywords
  const text = `${intake.chiefComplaint} ${intake.symptoms}`.toLowerCase();
  let severity: SeverityLevel = "low";
  if (text.includes("chest pain") || text.includes("unconscious") || text.includes("breathing") || text.includes("cardiac")) {
    severity = "critical";
  } else if (text.includes("fracture") || text.includes("bleeding") || text.includes("head injury")) {
    severity = "high";
  } else if (text.includes("fever") || text.includes("vomiting") || text.includes("abdominal")) {
    severity = "medium";
  }

  const actionSets: Record<SeverityLevel, string[]> = {
    critical: [
      "Establish IV access immediately",
      "Administer supplemental oxygen",
      "Prepare crash cart / intubation equipment",
      "Notify attending physician STAT",
      "Continuous cardiac monitoring",
    ],
    high: [
      "Administer pain management protocol",
      "Order STAT imaging (X-ray / CT)",
      "Apply pressure to bleeding site",
      "Notify attending physician within 15 min",
    ],
    medium: [
      "Administer antipyretics if febrile",
      "Obtain blood panel and urinalysis",
      "Monitor vitals every 30 minutes",
      "Schedule physician evaluation",
    ],
    low: [
      "Document vitals and chief complaint",
      "Schedule non-urgent physician evaluation",
      "Provide comfort measures",
    ],
  };

  const recommendations: Record<SeverityLevel, string> = {
    critical: "Immediate intervention required. Prepare for potential intubation and IV access. Activate trauma / cardiac team.",
    high: "Urgent attention needed. Stabilize patient and prepare for diagnostic imaging. Monitor closely.",
    medium: "Semi-urgent. Run standard diagnostics and monitor. Schedule physician evaluation within 1 hour.",
    low: "Non-urgent. Standard intake procedures. Patient can wait for scheduled evaluation.",
  };

  return {
    patient: intake,
    severity,
    recommendation: recommendations[severity],
    actions: actionSets[severity].map((text, i) => ({ id: `action-${i}`, text, checked: false })),
    escalation: severity === "critical",
  };
}

export const mockAuditLog: AuditEntry[] = [
  { id: "T-1001", timestamp: "2026-02-21 08:12", patientId: "P-4421", patientName: "James Carter", severity: "critical", actionTaken: "IV access, intubation prep, cardiac team alerted", overridden: false },
  { id: "T-1002", timestamp: "2026-02-21 08:34", patientId: "P-4422", patientName: "Maria Santos", severity: "high", actionTaken: "CT scan ordered, pain management started", overridden: false },
  { id: "T-1003", timestamp: "2026-02-21 09:01", patientId: "P-4423", patientName: "Robert Kim", severity: "medium", actionTaken: "Blood panel ordered, vitals monitoring", overridden: true },
  { id: "T-1004", timestamp: "2026-02-21 09:15", patientId: "P-4424", patientName: "Susan Okafor", severity: "low", actionTaken: "Standard intake, scheduled for evaluation", overridden: false },
  { id: "T-1005", timestamp: "2026-02-21 09:42", patientId: "P-4425", patientName: "David Chen", severity: "critical", actionTaken: "Crash cart deployed, attending notified STAT", overridden: false },
  { id: "T-1006", timestamp: "2026-02-21 10:05", patientId: "P-4426", patientName: "Emily Brown", severity: "medium", actionTaken: "Antipyretics administered, blood work ordered", overridden: false },
  { id: "T-1007", timestamp: "2026-02-21 10:23", patientId: "P-4427", patientName: "Ahmed Hassan", severity: "high", actionTaken: "Wound care, X-ray ordered, tetanus booster", overridden: true },
  { id: "T-1008", timestamp: "2026-02-21 10:50", patientId: "P-4428", patientName: "Lisa Park", severity: "low", actionTaken: "Comfort measures, scheduled non-urgent eval", overridden: false },
];
