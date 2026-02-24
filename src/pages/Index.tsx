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

const Index = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState<PatientIntake>({
    name: "",
    age: "",
    gender: "",
    chiefComplaint: "",
    symptoms: "",
  });
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [triageResult, setTriageResult] = useState<ReturnType<typeof getMockTriageResult> | null>(null);
  const [emergencyActivated, setEmergencyActivated] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);

  const canActivateEmergency = hasPermission(user?.role, "canActivateEmergency");

  const onSpeechResult = useCallback(
    (transcript: string) => {
      setForm((f) => ({
        ...f,
        symptoms: f.symptoms ? `${f.symptoms} ${transcript}` : transcript,
      }));
    },
    []
  );

  const speech = useSpeechRecognition({ onResult: onSpeechResult });

  const update = (field: keyof PatientIntake, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const canSubmit = form.name && form.age && form.gender && form.chiefComplaint && form.symptoms;

  const handleSubmit = () => {
    if (!canSubmit) return;
    const result = getMockTriageResult(form);
    setTriageResult(result);
    setIsProcessing(true);
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);
    if (triageResult) {
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
    const newFiles = Array.from(e.dataTransfer.files).map((f) => f.name);
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map((f) => f.name);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

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
              size="lg"
              className={`h-14 px-8 text-base font-bold ${
                emergencyActivated
                  ? 'bg-muted text-muted-foreground cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
              aria-label={emergencyActivated ? "Emergency response activated" : "Activate emergency response"}
            >
              {emergencyActivated ? (
                <>
                  <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  EMERGENCY ACTIVATED
                </>
              ) : (
                <>
                  <ShieldAlert className="mr-2 h-5 w-5" aria-hidden="true" />
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
            <Input id="complaint" placeholder="e.g. Chest pain, difficulty breathing" className="h-12 text-base" value={form.chiefComplaint} onChange={(e) => update("chiefComplaint", e.target.value)} />
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
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label className="text-base">Attach Files (optional)</Label>
            <label
              className={`flex min-h-[100px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors ${
                dragOver ? "border-primary bg-accent" : "border-border hover:border-primary/50"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Drag & drop patient history or protocol PDFs, or click to browse
              </span>
              <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx" onChange={handleFileInput} />
            </label>
            {files.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {files.map((f, i) => (
                  <li key={i}>📎 {f}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Submit */}
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="h-16 w-full text-xl font-bold"
            size="lg"
            aria-label="Analyze patient and generate triage assessment"
          >
            Analyze Patient
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
