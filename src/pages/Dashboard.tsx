import { useState, useCallback, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { type TriageResult, severityConfig } from "@/lib/mock-data";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { OverridePanel, type OverrideData } from "@/components/OverridePanel";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";

const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = (location.state as { result?: TriageResult })?.result;
  const { user } = useAuth();

  const [actions, setActions] = useState(result?.actions ?? []);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [emergencyActivated, setEmergencyActivated] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);

  const canOverride = hasPermission(user?.role, "canOverrideAI");
  const canActivateEmergency = hasPermission(user?.role, "canActivateEmergency");
  const canViewReasoning = hasPermission(user?.role, "canViewReasoning");

  // Scroll to top when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const handleEmergency = () => {
    setShowEmergencyConfirm(true);
  };

  const confirmEmergency = () => {
    setEmergencyActivated(true);
    console.log('EMERGENCY ACTIVATED for patient:', result?.patient.name);
  };

  const handleOverrideSubmit = (data: OverrideData) => {
    console.log('Override submitted:', data);
    // In real system: 
    // - Save override to database
    // - Log in audit trail with doctor credentials
    // - Update patient severity
    // - Notify medical team
    // - Generate audit report
    setOverrideOpen(false);
  };

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

  const { patient, severity, confidence, reasoningFactors, recommendation, escalation } = result;
  const sev = severityConfig[severity];

  const toggleAction = (id: string) =>
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, checked: !a.checked } : a)));

  return (
    <main id="main-content" className="container max-w-3xl py-8 space-y-6" role="main">
      {/* Back and Emergency Button Row */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate("/")} className="h-10 text-base">
          <ArrowLeft className="mr-2 h-5 w-5" /> New Intake
        </Button>
        
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
      {emergencyActivated && (
        <Alert className="border-2 border-red-600 bg-red-50 dark:bg-red-950">
          <ShieldAlert className="h-6 w-6 text-red-600" />
          <AlertTitle className="text-lg font-bold text-red-600">Emergency Response Activated</AlertTitle>
          <AlertDescription className="text-base text-red-600">
            Trauma/cardiac team has been alerted. Attending physician notified STAT. Emergency protocols initiated.
          </AlertDescription>
        </Alert>
      )}

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

      {/* Severity Badge with Confidence */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className={`inline-flex items-center rounded-lg px-5 py-3 text-2xl font-black tracking-wider ${sev.className}`}>
          {sev.label}
        </span>
        <div className="flex flex-col">
          <span className="text-lg text-muted-foreground">Triage Severity</span>
          <div className="flex items-center gap-2 mt-1">
            <div className="h-2 w-32 bg-muted rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary" 
                style={{ width: `${confidence}%` }}
              ></div>
            </div>
            <span className="text-sm font-bold text-primary">{confidence}% Confidence</span>
          </div>
        </div>
      </div>

      {/* AI Reasoning - Only for doctors and admins */}
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

      {/* Patient Context */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Patient Context</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">Name</p>
              <p className="font-medium">{patient.name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Age</p>
              <p className="font-medium">{patient.age}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Gender</p>
              <p className="font-medium capitalize">{patient.gender}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Chief Complaint</p>
              <p className="font-medium">{patient.chiefComplaint}</p>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm text-muted-foreground">Symptoms</p>
            <p className="mt-1">{patient.symptoms}</p>
          </div>
        </CardContent>
      </Card>

      {/* AI Recommendation */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Recommendation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-base">{recommendation}</p>
        </CardContent>
      </Card>

      {/* Recommended Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {actions.map((action) => (
            <label key={action.id} className="flex items-start gap-3 cursor-pointer group">
              <Checkbox
                checked={action.checked}
                onCheckedChange={() => toggleAction(action.id)}
                className="mt-1"
              />
              <span className="text-base group-hover:text-foreground transition-colors">
                {action.text}
              </span>
            </label>
          ))}
        </CardContent>
      </Card>

      {/* Override Section - Only for doctors */}
      {canOverride && (
        <>
          {!overrideOpen ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-severity-high" />
                  Override AI Assessment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  onClick={() => setOverrideOpen(true)}
                  className="h-12 w-full text-base"
                >
                  Override Triage Decision
                </Button>
              </CardContent>
            </Card>
          ) : (
            <OverridePanel
              patientId={patient.name}
              patientName={patient.name}
              currentSeverity={severity}
              onSubmit={handleOverrideSubmit}
              onCancel={() => setOverrideOpen(false)}
            />
          )}
        </>
      )}

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
  );
};

export default Dashboard;
