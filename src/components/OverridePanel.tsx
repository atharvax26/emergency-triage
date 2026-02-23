import { useState } from "react";
import { AlertTriangle, Mic, MicOff, Lock, User, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useSpeechRecognition } from "@/hooks/use-speech-recognition";
import { ConfirmationDialog } from "./ConfirmationDialog";
import { useCallback } from "react";

interface OverridePanelProps {
  patientId: string;
  patientName: string;
  currentSeverity: string;
  onSubmit: (data: OverrideData) => void;
  onCancel: () => void;
}

export interface OverrideData {
  newSeverity: string;
  reason: string;
  clinicalJustification: string;
  doctorName: string;
  doctorId: string;
  doctorPin: string;
  timestamp: string;
}

const overrideReasons = [
  "Clinical examination reveals different severity",
  "Patient history indicates higher risk",
  "Vital signs not captured by AI assessment",
  "Recent lab results change assessment",
  "Patient deterioration observed",
  "Comorbidities require escalation",
  "Protocol requires manual override",
  "Other (specify in justification)",
];

export function OverridePanel({
  patientId,
  patientName,
  currentSeverity,
  onSubmit,
  onCancel,
}: OverridePanelProps) {
  const [step, setStep] = useState<"form" | "auth">("form");
  const [showConfirm, setShowConfirm] = useState(false);
  
  // Form data
  const [newSeverity, setNewSeverity] = useState("");
  const [reason, setReason] = useState("");
  const [justification, setJustification] = useState("");
  
  // Auth data
  const [doctorName, setDoctorName] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [doctorPin, setDoctorPin] = useState("");

  const onSpeechResult = useCallback(
    (transcript: string) => {
      setJustification((prev) => (prev ? `${prev} ${transcript}` : transcript));
    },
    []
  );

  const speech = useSpeechRecognition({ onResult: onSpeechResult });

  const canProceedToAuth = newSeverity && reason && justification.length >= 20;
  const canSubmit = doctorName && doctorId && doctorPin.length === 4;

  const handleProceedToAuth = () => {
    setStep("auth");
  };

  const handleSubmitOverride = () => {
    setShowConfirm(true);
  };

  const confirmSubmit = () => {
    const data: OverrideData = {
      newSeverity,
      reason,
      clinicalJustification: justification,
      doctorName,
      doctorId,
      doctorPin,
      timestamp: new Date().toISOString(),
    };
    onSubmit(data);
  };

  return (
    <>
      <Card className="border-2 border-severity-high">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-severity-high" />
            Override AI Triage Assessment
          </CardTitle>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant="outline" className="text-xs">
              Patient: {patientName}
            </Badge>
            <Badge variant="outline" className="text-xs">
              ID: {patientId}
            </Badge>
            <Badge variant="outline" className="text-xs">
              Current: {currentSeverity.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {step === "form" ? (
            <div className="space-y-6">
              {/* Step Indicator */}
              <div className="flex items-center gap-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                    1
                  </div>
                  <span className="font-medium">Clinical Assessment</span>
                </div>
                <div className="h-px flex-1 bg-border"></div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 text-xs font-bold">
                    2
                  </div>
                  <span>Authentication</span>
                </div>
              </div>

              {/* New Severity */}
              <div className="space-y-2">
                <Label htmlFor="newSeverity" className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  New Severity Level
                </Label>
                <Select value={newSeverity} onValueChange={setNewSeverity}>
                  <SelectTrigger className="h-12 text-base">
                    <SelectValue placeholder="Select new severity level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="critical">CRITICAL</SelectItem>
                    <SelectItem value="high">HIGH</SelectItem>
                    <SelectItem value="medium">MEDIUM</SelectItem>
                    <SelectItem value="low">LOW</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Override Reason */}
              <div className="space-y-2">
                <Label htmlFor="reason" className="text-base flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Override Reason
                </Label>
                <Select value={reason} onValueChange={setReason}>
                  <SelectTrigger className="h-12 text-base">
                    <SelectValue placeholder="Select reason for override" />
                  </SelectTrigger>
                  <SelectContent>
                    {overrideReasons.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Clinical Justification */}
              <div className="space-y-2">
                <Label htmlFor="justification" className="text-base mb-2 block">
                  Clinical Justification (minimum 20 characters)
                </Label>
                <div className="relative">
                  <Textarea
                    id="justification"
                    placeholder="Provide detailed clinical justification for this override. Include relevant observations, vital signs, patient history, or other clinical factors..."
                    className="min-h-[120px] pr-14 text-base"
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                  />
                  <div className="absolute right-2 bottom-2 text-xs text-muted-foreground">
                    {justification.length}/20 min
                  </div>
                  {speech.isListening && (
                    <div className="absolute left-2 bottom-2 flex items-center gap-2 rounded-md bg-red-50 dark:bg-red-950 px-2 py-1 text-xs text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800">
                      <div className="flex gap-1">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                      </div>
                      <span className="font-medium">Recording</span>
                    </div>
                  )}
                  <TooltipProvider>
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
                          ? "Voice input not supported"
                          : speech.isListening
                          ? "Stop recording"
                          : "Start voice input"}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <Button
                  onClick={handleProceedToAuth}
                  disabled={!canProceedToAuth}
                  className="h-12 text-base flex-1"
                >
                  Proceed to Authentication
                </Button>
                <Button variant="ghost" onClick={onCancel} className="h-12 text-base">
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Step Indicator */}
              <div className="flex items-center gap-2 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                    ✓
                  </div>
                  <span>Clinical Assessment</span>
                </div>
                <div className="h-px flex-1 bg-border"></div>
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                    2
                  </div>
                  <span className="font-medium">Authentication</span>
                </div>
              </div>

              {/* Auth Warning */}
              <div className="rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 p-4">
                <div className="flex items-start gap-3">
                  <Lock className="h-5 w-5 text-amber-600 mt-0.5" />
                  <div>
                    <p className="font-bold text-amber-900 dark:text-amber-100">
                      Doctor Authentication Required
                    </p>
                    <p className="text-sm text-amber-700 dark:text-amber-200 mt-1">
                      This override will be logged in the audit trail with your credentials. Ensure all
                      information is accurate.
                    </p>
                  </div>
                </div>
              </div>

              {/* Doctor Name */}
              <div className="space-y-2">
                <Label htmlFor="doctorName" className="text-base flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Doctor Name
                </Label>
                <Input
                  id="doctorName"
                  placeholder="Dr. [Full Name]"
                  className="h-12 text-base"
                  value={doctorName}
                  onChange={(e) => setDoctorName(e.target.value)}
                />
              </div>

              {/* Doctor ID */}
              <div className="space-y-2">
                <Label htmlFor="doctorId" className="text-base">Medical License / Staff ID</Label>
                <Input
                  id="doctorId"
                  placeholder="e.g., MD-12345 or Staff-6789"
                  className="h-12 text-base font-mono"
                  value={doctorId}
                  onChange={(e) => setDoctorId(e.target.value)}
                />
              </div>

              {/* PIN */}
              <div className="space-y-2">
                <Label htmlFor="doctorPin" className="text-base flex items-center gap-2">
                  <Lock className="h-4 w-4" />
                  4-Digit PIN
                </Label>
                <Input
                  id="doctorPin"
                  type="password"
                  placeholder="••••"
                  maxLength={4}
                  className="h-12 text-base font-mono text-center text-2xl tracking-widest"
                  value={doctorPin}
                  onChange={(e) => setDoctorPin(e.target.value.replace(/\D/g, ""))}
                />
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <Button variant="ghost" onClick={() => setStep("form")} className="h-12 text-base">
                  Back
                </Button>
                <Button
                  onClick={handleSubmitOverride}
                  disabled={!canSubmit}
                  className="h-12 text-base flex-1 bg-severity-high hover:bg-severity-high/90"
                >
                  Submit Override
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        onConfirm={confirmSubmit}
        title="Confirm Override Submission"
        description={`You are about to override the AI triage assessment for ${patientName} (${patientId}). This action will be permanently logged in the audit trail with your credentials: ${doctorName} (${doctorId}). Do you want to proceed?`}
        confirmText="Yes, Submit Override"
        cancelText="Cancel"
        variant="destructive"
      />
    </>
  );
}
