import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Mic, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { type TriageResult, severityConfig } from "@/lib/mock-data";

const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = (location.state as { result?: TriageResult })?.result;

  const [actions, setActions] = useState(result?.actions ?? []);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideText, setOverrideText] = useState("");

  if (!result) {
    return (
      <main className="container max-w-3xl py-16 text-center">
        <h1 className="mb-4 text-2xl font-bold">No Triage Data</h1>
        <p className="mb-6 text-muted-foreground">Submit a patient intake first to see triage results.</p>
        <Button onClick={() => navigate("/")} size="lg" className="h-12 text-base">
          <ArrowLeft className="mr-2 h-5 w-5" /> Go to Intake
        </Button>
      </main>
    );
  }

  const { patient, severity, recommendation, escalation } = result;
  const sev = severityConfig[severity];

  const toggleAction = (id: string) =>
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, checked: !a.checked } : a)));

  return (
    <main className="container max-w-3xl py-8 space-y-6">
      {/* Back */}
      <Button variant="ghost" onClick={() => navigate("/")} className="h-10 text-base">
        <ArrowLeft className="mr-2 h-5 w-5" /> New Intake
      </Button>

      {/* Escalation Banner */}
      {escalation && (
        <Alert variant="destructive" className="border-2">
          <ShieldAlert className="h-6 w-6" />
          <AlertTitle className="text-lg font-bold">CRITICAL ESCALATION</AlertTitle>
          <AlertDescription className="text-base">
            This patient requires immediate intervention. Trauma / cardiac team should be alerted.
          </AlertDescription>
        </Alert>
      )}

      {/* Severity Badge */}
      <div className="flex items-center gap-4">
        <span className={`inline-flex items-center rounded-lg px-5 py-3 text-2xl font-black tracking-wider ${sev.className}`}>
          {sev.label}
        </span>
        <span className="text-lg text-muted-foreground">Triage Severity</span>
      </div>

      {/* Patient Context */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Patient Context</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">Name</p>
              <p className="font-semibold">{patient.name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Age</p>
              <p className="font-semibold">{patient.age}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Gender</p>
              <p className="font-semibold capitalize">{patient.gender}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Chief Complaint</p>
              <p className="font-semibold">{patient.chiefComplaint}</p>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm text-muted-foreground">Symptoms</p>
            <p>{patient.symptoms}</p>
          </div>
        </CardContent>
      </Card>

      {/* AI Recommendation */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Recommendation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-base leading-relaxed">{recommendation}</p>
        </CardContent>
      </Card>

      {/* Action Checklist */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {actions.map((action) => (
            <label
              key={action.id}
              className="flex cursor-pointer items-center gap-3 rounded-md border p-3 hover:bg-accent"
            >
              <Checkbox
                checked={action.checked}
                onCheckedChange={() => toggleAction(action.id)}
                className="h-5 w-5"
              />
              <span className={`text-base ${action.checked ? "line-through text-muted-foreground" : ""}`}>
                {action.text}
              </span>
            </label>
          ))}
        </CardContent>
      </Card>

      {/* Override */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-severity-high" />
            Override AI Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!overrideOpen ? (
            <Button variant="outline" onClick={() => setOverrideOpen(true)} className="h-12 text-base">
              Override with Manual Assessment
            </Button>
          ) : (
            <div className="space-y-3">
              <Label className="text-base">Your Assessment</Label>
              <div className="relative">
                <Textarea
                  placeholder="Enter your clinical assessment..."
                  className="min-h-[100px] pr-14 text-base"
                  value={overrideText}
                  onChange={(e) => setOverrideText(e.target.value)}
                />
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-2 h-10 w-10 text-muted-foreground hover:text-foreground"
                      >
                        <Mic className="h-5 w-5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Coming soon</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <div className="flex gap-3">
                <Button className="h-12 text-base" disabled={!overrideText}>
                  Submit Override
                </Button>
                <Button variant="ghost" className="h-12 text-base" onClick={() => { setOverrideOpen(false); setOverrideText(""); }}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
};

export default Dashboard;
