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
  confidence: number;
  reasoningFactors: string[];
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
  let confidence = 85;
  let reasoningFactors: string[] = [];

  // Critical: life-threatening cardiac, respiratory, neurological, or hemorrhagic emergencies
  const isCritical =
    text.includes("chest pain") ||
    text.includes("unconscious") ||
    text.includes("unresponsive") ||
    text.includes("not breathing") ||
    text.includes("difficulty breathing") ||
    text.includes("shortness of breath") ||
    text.includes("cardiac") ||
    text.includes("heart attack") ||
    text.includes("stroke") ||
    text.includes("seizure") ||
    text.includes("anaphylaxis") ||
    text.includes("severe allergic") ||
    text.includes("massive bleeding") ||
    text.includes("hemorrhage") ||
    text.includes("overdose") ||
    text.includes("poisoning") ||
    text.includes("septic shock") ||
    text.includes("loss of consciousness");

  // High: urgent conditions requiring prompt evaluation — trauma, oncological red flags, acute organ symptoms
  const isHigh =
    text.includes("fracture") ||
    text.includes("bleeding") ||
    text.includes("head injury") ||
    text.includes("lump") ||
    text.includes("mass") ||
    text.includes("tumor") ||
    text.includes("breast lump") ||
    text.includes("breast pain") ||
    text.includes("nipple discharge") ||
    text.includes("blood in urine") ||
    text.includes("hematuria") ||
    text.includes("rectal bleeding") ||
    text.includes("coughing blood") ||
    text.includes("hemoptysis") ||
    text.includes("sudden vision") ||
    text.includes("sudden weakness") ||
    text.includes("sudden numbness") ||
    text.includes("severe headache") ||
    text.includes("worst headache") ||
    text.includes("testicular pain") ||
    text.includes("testicular swelling") ||
    text.includes("acute abdomen") ||
    text.includes("appendicitis") ||
    text.includes("ectopic") ||
    text.includes("deep vein") ||
    text.includes("dvt") ||
    text.includes("pulmonary embolism") ||
    text.includes("pe ");

  // Medium: significant but non-immediately-life-threatening symptoms
  const isMedium =
    text.includes("fever") ||
    text.includes("vomiting") ||
    text.includes("abdominal") ||
    text.includes("tenderness") ||
    text.includes("pain in breast") ||
    text.includes("breast tenderness") ||
    text.includes("lactation") ||
    text.includes("mastitis") ||
    text.includes("infection") ||
    text.includes("urinary tract") ||
    text.includes("uti") ||
    text.includes("dysuria") ||
    text.includes("diarrhea") ||
    text.includes("dehydration") ||
    text.includes("migraine") ||
    text.includes("dizziness") ||
    text.includes("fainting") ||
    text.includes("syncope") ||
    text.includes("palpitations") ||
    text.includes("swelling") ||
    text.includes("rash") ||
    text.includes("allergic reaction") ||
    text.includes("asthma") ||
    text.includes("back pain") ||
    text.includes("kidney") ||
    text.includes("nausea") ||
    text.includes("anxiety") ||
    text.includes("panic attack");

  if (isCritical) {
    severity = "critical";
    confidence = 94;
    reasoningFactors = [
      "Symptoms indicate a potentially life-threatening emergency",
      "Immediate stabilization and intervention required",
      "Activate emergency response protocol"
    ];
  } else if (isHigh) {
    severity = "high";
    confidence = 89;
    // Specific reasoning for breast/oncological presentations
    if (text.includes("lump") || text.includes("mass") || text.includes("breast lump") || text.includes("breast pain") || text.includes("nipple discharge")) {
      reasoningFactors = [
        "Breast lump or mass requires urgent oncological evaluation",
        "Cannot rule out malignancy without imaging and clinical assessment",
        "Prompt referral for mammogram / ultrasound indicated"
      ];
    } else {
      reasoningFactors = [
        "Urgent condition requiring prompt clinical assessment",
        "Risk of deterioration if evaluation is delayed",
        "Diagnostic workup and specialist notification required"
      ];
    }
  } else if (isMedium) {
    severity = "medium";
    confidence = 82;
    // Specific reasoning for breast infection/lactation presentations
    if (text.includes("tenderness") || text.includes("lactation") || text.includes("mastitis") || text.includes("pain in breast") || text.includes("breast tenderness")) {
      reasoningFactors = [
        "Breast tenderness with lactation may indicate mastitis or blocked duct",
        "Requires clinical examination and possible antibiotic therapy",
        "Monitor for signs of abscess formation"
      ];
    } else {
      reasoningFactors = [
        "Symptoms suggest moderate medical concern",
        "Requires diagnostic workup within 1 hour",
        "No immediate life-threatening indicators"
      ];
    }
  } else {
    severity = "low";
    confidence = 78;
    reasoningFactors = [
      "Symptoms indicate non-urgent condition",
      "No critical warning signs detected",
      "Standard evaluation protocol appropriate"
    ];
  }

  // Determine context-specific actions
  const isBreastOncology = text.includes("lump") || text.includes("mass") || text.includes("breast lump") || text.includes("nipple discharge");
  const isBreastInfection = text.includes("tenderness") || text.includes("lactation") || text.includes("mastitis") || text.includes("pain in breast") || text.includes("breast tenderness");

  const actionSets: Record<SeverityLevel, string[]> = {
    critical: [
      "Establish IV access immediately",
      "Administer supplemental oxygen",
      "Prepare crash cart / intubation equipment",
      "Notify attending physician STAT",
      "Continuous cardiac monitoring",
    ],
    high: isBreastOncology ? [
      "Perform clinical breast examination",
      "Order urgent mammogram and/or breast ultrasound",
      "Refer to oncology / breast surgery team",
      "Document lump characteristics (size, mobility, texture)",
      "Notify attending physician within 15 min",
    ] : [
      "Administer pain management protocol",
      "Order STAT imaging (X-ray / CT)",
      "Apply pressure to bleeding site if applicable",
      "Notify attending physician within 15 min",
    ],
    medium: isBreastInfection ? [
      "Perform breast examination for signs of abscess",
      "Obtain CBC and inflammatory markers",
      "Assess for fever and systemic infection signs",
      "Initiate antibiotic therapy if mastitis confirmed",
      "Advise on continued breastfeeding or pumping",
    ] : [
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
    high: isBreastOncology
      ? "Urgent evaluation required. Breast lump cannot be dismissed without imaging. Refer to breast surgery or oncology team promptly."
      : "Urgent attention needed. Stabilize patient and prepare for diagnostic imaging. Monitor closely.",
    medium: isBreastInfection
      ? "Semi-urgent. Evaluate for mastitis or breast abscess. Initiate appropriate antibiotic therapy and monitor for complications."
      : "Semi-urgent. Run standard diagnostics and monitor. Schedule physician evaluation within 1 hour.",
    low: "Non-urgent. Standard intake procedures. Patient can wait for scheduled evaluation.",
  };

  return {
    patient: intake,
    severity,
    confidence,
    reasoningFactors,
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
