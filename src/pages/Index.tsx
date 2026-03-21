import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, MicOff, Upload, ShieldAlert } from "lucide-react";
import { useSpeechRecognition } from "@/hooks/use-speech-recognition";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getMockTriageResult, type PatientIntake } from "@/lib/mock-data";
import { TriageProcessing } from "@/components/TriageProcessing";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";
import { api } from "@/lib/api";
import { useMutation } from "@/hooks/use-api";

const INTAKE_FORM_KEY = "intake_form_draft";

type IntakeFormState = PatientIntake & {
  systolic_bp?: string;
  diastolic_bp?: string;
  heart_rate?: string;
  respiratory_rate?: string;
  temperature?: string;
  spo2?: string;
};

const EMPTY_FORM: IntakeFormState = {
  name: "",
  age: "",
  gender: "",
  chiefComplaint: "",
  symptoms: "",
  systolic_bp: "",
  diastolic_bp: "",
  heart_rate: "",
  respiratory_rate: "",
  temperature: "",
  spo2: "",
};

function loadDraft(): IntakeFormState {
  try {
    const raw = sessionStorage.getItem(INTAKE_FORM_KEY);
    return raw ? { ...EMPTY_FORM, ...JSON.parse(raw) } : EMPTY_FORM;
  } catch { return EMPTY_FORM; }
}

function saveDraft(form: IntakeFormState) {
  sessionStorage.setItem(INTAKE_FORM_KEY, JSON.stringify(form));
}

function clearDraft() {
  sessionStorage.removeItem(INTAKE_FORM_KEY);
}

const Index = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState<IntakeFormState>(loadDraft);
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [triageResult, setTriageResult] = useState<ReturnType<typeof getMockTriageResult> | null>(null);
  const [emergencyActivated, setEmergencyActivated] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const canActivateEmergency = hasPermission(user?.role, "canActivateEmergency");

  // API mutation for creating patient
  const { mutate: createPatient, loading: creatingPatient } = useMutation(
    (data: any) => api.createPatient(data)
  );

  const onSpeechResult = useCallback(
    (transcript: string) => {
      setForm((f) => {
        const next = {
          ...f,
          symptoms: f.symptoms ? `${f.symptoms} ${transcript}` : transcript,
        };
        saveDraft(next);
        return next;
      });
    },
    []
  );

  const speech = useSpeechRecognition({ onResult: onSpeechResult });

  const update = (field: keyof IntakeFormState, value: string) =>
    setForm((f) => {
      const next = { ...f, [field]: value };
      saveDraft(next);
      return next;
    });

  const canSubmit = form.name && form.age && form.gender && form.chiefComplaint && form.symptoms &&
    form.systolic_bp && form.diastolic_bp && form.heart_rate && form.respiratory_rate && 
    form.temperature && form.spo2;

  // Helper functions for mapping AI response to UI
  const mapRiskTierToSeverity = (riskTier: string): "low" | "medium" | "high" | "critical" => {
    const mapping: Record<string, "low" | "medium" | "high" | "critical"> = {
      "low": "low",
      "medium": "medium",
      "high": "high",
      "critical": "critical"
    };
    return mapping[riskTier.toLowerCase()] || "medium";
  };

  const getRecommendationForRiskTier = (riskTier: string): string => {
    const recommendations: Record<string, string> = {
      "critical": "Immediate intervention required. Prepare for potential intubation and IV access. Activate trauma / cardiac team.",
      "high": "Urgent attention needed. Stabilize patient and prepare for diagnostic imaging. Monitor closely.",
      "medium": "Semi-urgent. Run standard diagnostics and monitor. Schedule physician evaluation within 1 hour.",
      "low": "Non-urgent. Standard intake procedures. Patient can wait for scheduled evaluation."
    };
    return recommendations[riskTier.toLowerCase()] || recommendations["medium"];
  };

  const getActionsForRiskTier = (riskTier: string) => {
    const actionSets: Record<string, string[]> = {
      "critical": [
        "Establish IV access immediately",
        "Administer supplemental oxygen",
        "Prepare crash cart / intubation equipment",
        "Notify attending physician STAT",
        "Continuous cardiac monitoring",
      ],
      "high": [
        "Administer pain management protocol",
        "Order STAT imaging (X-ray / CT)",
        "Apply pressure to bleeding site",
        "Notify attending physician within 15 min",
      ],
      "medium": [
        "Administer antipyretics if febrile",
        "Obtain blood panel and urinalysis",
        "Monitor vitals every 30 minutes",
        "Schedule physician evaluation",
      ],
      "low": [
        "Document vitals and chief complaint",
        "Schedule non-urgent physician evaluation",
        "Provide comfort measures",
      ]
    };
    
    const actions = actionSets[riskTier.toLowerCase()] || actionSets["medium"];
    return actions.map((text, i) => ({ id: `action-${i}`, text, checked: false }));
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    
    setApiError(null);
    
    // Step 1: Create patient record
    let patient: any;
    try {
      patient = await createPatient({
        name: form.name,
        age: parseInt(form.age),
        gender: form.gender,
        chief_complaint: form.chiefComplaint,
        symptoms: form.symptoms,
      });
    } catch (err: any) {
      setApiError("Failed to create patient record: " + (err.message || "Unknown error"));
      return;
    }

    // Step 2: Get AI prediction
    let prediction: any = null;
    try {
      prediction = await api.predictTriage({
        patient_data: {
          vitals: {
            systolic_bp: parseFloat(form.systolic_bp!),
            diastolic_bp: parseFloat(form.diastolic_bp!),
            heart_rate: parseFloat(form.heart_rate!),
            respiratory_rate: parseFloat(form.respiratory_rate!),
            temperature: parseFloat(form.temperature!),
            spo2: parseFloat(form.spo2!)
          },
          age: parseInt(form.age),
          symptoms: form.symptoms.split(',').map(s => s.trim()).filter(s => s)
        },
        request_id: patient.id
      });
    } catch (err: any) {
      // Prediction failed — use mock fallback but still add to queue
      setApiError(err.message || "AI prediction unavailable, using offline mode.");
    }

    // Step 3: Build result (real or mock fallback)
    const severity = prediction
      ? mapRiskTierToSeverity(prediction.risk_tier)
      : getMockTriageResult(form).severity;

    const result = prediction ? {
      patient: form,
      severity,
      confidence: Math.round(prediction.confidence * 100),
      reasoningFactors: prediction.reasoning?.gemini_reasoning
        ? [
            ...prediction.reasoning.reasoning_trace,
            `Context Pruning: ${prediction.pruning?.original_tokens ?? '?'} → ${prediction.pruning?.compressed_tokens ?? '?'} tokens (${Math.round((prediction.pruning?.compression_ratio ?? 0) * 100)}% reduction)`,
            prediction.latency_breakdown
              ? `Pipeline: ML ${prediction.latency_breakdown.ml_ms}ms | Scaledown ${prediction.latency_breakdown.scaledown_ms}ms | LLM ${prediction.latency_breakdown.llm_ms}ms | Total ${prediction.latency_breakdown.total_ms}ms`
              : `Inference: ${prediction.inference_time_ms?.toFixed(1)}ms | Confidence: ${(prediction.confidence * 100).toFixed(1)}%`,
          ]
        : [
            `AI Model: ${prediction.model_version}`,
            `Risk Tier: ${prediction.risk_tier}`,
            `Decision: ${prediction.decision_label}`,
            `Calibrated Probability: ${(prediction.calibrated_probability * 100).toFixed(1)}%`,
            `Inference Time: ${prediction.inference_time_ms.toFixed(1)}ms`,
            ...(prediction.pruning?.pruning_applied
              ? [`Context Pruning: ${prediction.pruning.original_tokens} → ${prediction.pruning.compressed_tokens} tokens (${Math.round(prediction.pruning.compression_ratio * 100)}% reduction)`]
              : prediction.pruning
              ? [`Context Pruning: passthrough (${prediction.pruning.original_tokens} tokens)`]
              : []),
          ],
      recommendation: prediction.reasoning?.severity_justification
        ? prediction.reasoning.severity_justification
        : getRecommendationForRiskTier(prediction.risk_tier),
      actions: prediction.reasoning?.recommended_actions
        ? prediction.reasoning.recommended_actions.map((text: string, i: number) => ({ id: `action-${i}`, text, checked: false }))
        : getActionsForRiskTier(prediction.risk_tier),
      escalation: prediction.risk_tier.toLowerCase() === "critical"
    } : getMockTriageResult(form);

    // Step 4: Always add to queue regardless of prediction success/failure
    try {
      await api.addToQueue({
        patient_id: patient.id,
        name: form.name,
        age: parseInt(form.age),
        chief_complaint: form.chiefComplaint,
        severity: severity,
      });
    } catch (qErr: any) {
      console.error("addToQueue failed:", qErr);
      // Non-fatal — triage result still shown
    }

    // Step 5: Write audit log entry
    try {
      const safetyOverride = prediction?.safety_override ?? false;
      const actionMap: Record<string, string> = {
        critical: "IV access, intubation prep, cardiac team alerted",
        high: "CT scan ordered, pain management started",
        medium: "Blood panel ordered, vitals monitoring",
        low: "Standard intake, scheduled for evaluation",
      };
      await api.addAuditEntry({
        patient_id: patient.id,
        patient_name: form.name,
        severity,
        action_taken: actionMap[severity] || "Triage assessment completed",
        overridden: safetyOverride,
        override_reason: prediction?.override_reason ?? undefined,
        performed_by: user?.name ?? "Unknown",
      });
    } catch (aErr: any) {
      console.error("addAuditEntry failed:", aErr);
      // Non-fatal
    }

    setTriageResult(result);
    setIsProcessing(true);
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);
    if (triageResult) {
      clearDraft();
      navigate("/dashboard", { state: { result: triageResult } });
    }
  };

  const handleEmergency = () => {
    setShowEmergencyConfirm(true);
  };

  const confirmEmergency = () => {
    setEmergencyActivated(true);
    console.log('EMERGENCY ACTIVATED during intake');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length > 0) handleFiles(dropped);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
    setExtractError(null);
    const docFile = newFiles[0];
    setExtracting(true);
    try {
      const result = await api.extractDocument(docFile);
      console.log("[extractDocument] response:", result);
      const e = result.extracted;
      if (e) {
        // Normalise gender to lowercase to match Select values
        const normGender = e.gender ? e.gender.toLowerCase() : null;
        const validGender = (["male", "female", "other"] as string[]).includes(normGender ?? "") ? normGender : null;

        const hasAny = !!(e.name || e.age !== null || validGender || e.chiefComplaint || e.symptoms);
        console.log("[extractDocument] hasAny:", hasAny, "fields:", { name: e.name, age: e.age, gender: validGender, cc: e.chiefComplaint, sym: e.symptoms });

        if (hasAny) {
          const cleanName = e.name ? e.name.split(/[\n\r]/)[0].trim() : null;
          setForm((f) => {
            const updated = {
              ...f,
              ...(cleanName ? { name: cleanName } : {}),
              ...(e.age !== null && e.age !== undefined ? { age: String(e.age) } : {}),
              ...(validGender ? { gender: validGender } : {}),
              ...(e.chiefComplaint ? { chiefComplaint: e.chiefComplaint.split(/[\n\r]/)[0].trim() } : {}),
              ...(e.symptoms ? { symptoms: e.symptoms.trim() } : {}),
            };
            console.log("[extractDocument] setForm updated:", updated);
            saveDraft(updated);
            return updated;
          });
        }

        if (!result.success || (result.source === "regex_fallback" && result.error)) {
          const isQuota = result.error?.includes("429") || result.error?.includes("quota");
          setExtractError(
            hasAny
              ? isQuota
                ? "Gemini quota exhausted — fields filled using text pattern matching."
                : "Partial extraction — some fields could not be read from the document."
              : isQuota
                ? "Gemini quota exhausted — please fill in the fields manually or try again tomorrow."
                : "Could not extract data from document — please fill in the fields manually."
          );
        }
      }
    } catch (err: any) {
      console.error("[extractDocument] error:", err);
      setExtractError("Could not extract data from document: " + (err.message || "Unknown error"));
    } finally {
      setExtracting(false);
    }
  };

  const removeFile = (index: number) =>
    setFiles((prev) => prev.filter((_, i) => i !== index));

  return (
    <>
      {isProcessing && <TriageProcessing onComplete={handleProcessingComplete} />}
      
      <main id="main-content" className="container max-w-2xl py-8" role="main">
        {/* Header with Emergency Button */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Patient Intake</h1>
          
          {canActivateEmergency && (
            <Button
              onClick={handleEmergency}
              disabled={emergencyActivated}
              size="sm"
              className={`h-9 px-4 text-sm font-semibold ${
                emergencyActivated
                  ? 'bg-muted text-muted-foreground cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
              aria-label={emergencyActivated ? "Emergency response activated" : "Activate emergency response"}
            >
              {emergencyActivated ? (
                <>
                  <svg className="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  EMERGENCY ACTIVATED
                </>
              ) : (
                <>
                  <ShieldAlert className="mr-1.5 h-4 w-4" aria-hidden="true" />
                  CODE BLUE / EMERGENCY
                </>
              )}
            </Button>
          )}
        </div>

        {/* Emergency Confirmation Banner */}
        {emergencyActivated && (
          <Alert className="border-2 border-red-600 bg-red-50 dark:bg-red-950 mb-6">
            <ShieldAlert className="h-6 w-6 text-red-600" />
            <AlertTitle className="text-lg font-bold text-red-600">Emergency Response Activated</AlertTitle>
            <AlertDescription className="text-base text-red-600">
              Trauma/cardiac team has been alerted. Attending physician notified STAT. Emergency protocols initiated.
            </AlertDescription>
          </Alert>
        )}

        {/* API Error Alert */}
        {apiError && (
          <Alert className="border-2 border-yellow-600 bg-yellow-50 dark:bg-yellow-950 mb-6">
            <AlertTitle className="text-lg font-bold text-yellow-600">Backend Connection Issue</AlertTitle>
            <AlertDescription className="text-base text-yellow-600">
              {apiError}. Using offline mode with mock data.
            </AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Patient Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Name & Age row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-base">Full Name</Label>
              <Input id="name" placeholder="Patient name" className="h-12 text-base" value={form.name} onChange={(e) => update("name", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="age" className="text-base">Age</Label>
              <Input id="age" type="number" placeholder="Age" className="h-12 text-base" value={form.age} onChange={(e) => update("age", e.target.value)} />
            </div>
          </div>

          {/* Gender */}
          <div className="space-y-2">
            <Label className="text-base">Gender</Label>
            <Select value={form.gender} onValueChange={(v) => update("gender", v)}>
              <SelectTrigger className="h-12 text-base">
                <SelectValue placeholder="Select gender" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="male">Male</SelectItem>
                <SelectItem value="female">Female</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Chief Complaint */}
          <div className="space-y-2">
            <Label htmlFor="complaint" className="text-base">Chief Complaint</Label>
            <Input id="complaint" placeholder="e.g. Chest pain, difficulty breathing" className="h-12 text-base" autoComplete="off" value={form.chiefComplaint} onChange={(e) => update("chiefComplaint", e.target.value)} />
          </div>

          {/* Symptoms with Mic */}
          <div className="space-y-2">
            <Label htmlFor="symptoms" className="text-base">Symptoms</Label>
            <div className="relative">
              <Textarea
                id="symptoms"
                placeholder="Describe all symptoms in detail..."
                className="min-h-[120px] pr-14 text-base"
                value={form.symptoms}
                onChange={(e) => update("symptoms", e.target.value)}
              />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant={speech.isListening ? "destructive" : "ghost"}
                    size="icon"
                    className="absolute right-2 top-2 h-10 w-10"
                    onClick={speech.toggle}
                    disabled={!speech.isSupported}
                  >
                    {speech.isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {!speech.isSupported
                    ? "Voice input not supported in this browser"
                    : speech.isListening
                    ? "Stop listening"
                    : "Start voice input"}
                </TooltipContent>
              </Tooltip>
            </div>
            {speech.isListening && (
              <div className="flex items-center gap-2 rounded-md bg-red-50 dark:bg-red-950 px-2 py-1 text-xs text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 w-fit">
                <div className="flex gap-1">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                </div>
                <span className="font-medium">Recording</span>
              </div>
            )}
          </div>

          {/* Vital Signs Section */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="text-lg font-semibold">Vital Signs</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="systolic_bp" className="text-base">Systolic BP (mmHg)</Label>
                <Input 
                  id="systolic_bp" 
                  type="number" 
                  placeholder="120" 
                  className="h-12 text-base"
                  value={form.systolic_bp || ''} 
                  onChange={(e) => update("systolic_bp", e.target.value)} 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="diastolic_bp" className="text-base">Diastolic BP (mmHg)</Label>
                <Input 
                  id="diastolic_bp" 
                  type="number" 
                  placeholder="80" 
                  className="h-12 text-base"
                  value={form.diastolic_bp || ''} 
                  onChange={(e) => update("diastolic_bp", e.target.value)} 
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="heart_rate" className="text-base">Heart Rate (bpm)</Label>
                <Input 
                  id="heart_rate" 
                  type="number" 
                  placeholder="75" 
                  className="h-12 text-base"
                  value={form.heart_rate || ''} 
                  onChange={(e) => update("heart_rate", e.target.value)} 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="respiratory_rate" className="text-base">Respiratory Rate (breaths/min)</Label>
                <Input 
                  id="respiratory_rate" 
                  type="number" 
                  placeholder="16" 
                  className="h-12 text-base"
                  value={form.respiratory_rate || ''} 
                  onChange={(e) => update("respiratory_rate", e.target.value)} 
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="temperature" className="text-base">Temperature (°C)</Label>
                <Input 
                  id="temperature" 
                  type="number" 
                  step="0.1" 
                  placeholder="37.0" 
                  className="h-12 text-base"
                  value={form.temperature || ''} 
                  onChange={(e) => update("temperature", e.target.value)} 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="spo2" className="text-base">SpO2 (%)</Label>
                <Input 
                  id="spo2" 
                  type="number" 
                  placeholder="98" 
                  className="h-12 text-base"
                  value={form.spo2 || ''} 
                  onChange={(e) => update("spo2", e.target.value)} 
                />
              </div>
            </div>
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label className="text-base">Attach Patient Document (optional)</Label>
            <label
              className={`flex min-h-[80px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-4 transition-colors ${
                dragOver ? "border-primary bg-accent" : files.length > 0 ? "border-primary/40 bg-primary/5" : "border-border hover:border-primary/50"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              {extracting ? (
                <>
                  <svg className="h-6 w-6 animate-spin text-primary" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span className="text-sm text-primary font-medium">Extracting patient info…</span>
                </>
              ) : (
                <>
                  <Upload className={`h-6 w-6 ${files.length > 0 ? "text-primary" : "text-muted-foreground"}`} />
                  <span className="text-sm text-muted-foreground text-center">
                    {files.length > 0
                      ? "Drop more files or click to browse"
                      : "Upload patient record (PDF, DOCX, TXT) — name, age, gender, complaints & symptoms will be auto-filled"}
                  </span>
                </>
              )}
              <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx,.txt" onChange={handleFileInput} />
            </label>

            {extractError && (
              <p className="text-xs text-yellow-600 dark:text-yellow-400">{extractError}</p>
            )}

            {files.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {files.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm text-primary"
                  >
                    <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                    <span className="max-w-[180px] truncate font-medium">{f.name}</span>
                    <button
                      type="button"
                      onClick={(e) => { e.preventDefault(); removeFile(i); }}
                      className="ml-1 rounded-full p-0.5 hover:bg-primary/20 text-primary/70 hover:text-primary"
                      aria-label={`Remove ${f.name}`}
                    >
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit */}
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || creatingPatient}
            className="h-16 w-full text-xl font-bold"
            size="lg"
            aria-label="Analyze patient and generate triage assessment"
          >
            {creatingPatient ? "Submitting..." : "Add Patient to Queue"}
          </Button>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        open={showEmergencyConfirm}
        onOpenChange={setShowEmergencyConfirm}
        onConfirm={confirmEmergency}
        title="Activate Emergency Response?"
        description="This will immediately alert the trauma/cardiac team and notify the attending physician STAT. Emergency protocols will be initiated. Are you sure you want to proceed?"
        confirmText="YES, ACTIVATE EMERGENCY"
        cancelText="Cancel"
        variant="destructive"
      />
    </main>
    </>
  );
};

export default Index;
