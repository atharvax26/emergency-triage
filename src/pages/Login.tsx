import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Stethoscope, HeartPulse, Shield, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { apiLogin, apiRegister, type UserRole } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const roles: { value: UserRole; label: string; icon: React.ReactNode; description: string }[] = [
  { value: "nurse",  label: "Nurse",  icon: <HeartPulse className="h-8 w-8" />,  description: "Triage intake & patient assessment" },
  { value: "doctor", label: "Doctor", icon: <Stethoscope className="h-8 w-8" />, description: "Full dashboard & override access" },
  { value: "admin",  label: "Admin",  icon: <Shield className="h-8 w-8" />,       description: "System management & audit logs" },
];

function RoleGrid({ selected, onSelect }: { selected: UserRole | ""; onSelect: (r: UserRole) => void }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {roles.map((role) => (
        <button key={role.value} type="button" onClick={() => onSelect(role.value)}
          className={cn(
            "flex flex-col items-center gap-2 rounded-lg border-2 p-4 text-center transition-colors",
            selected === role.value
              ? "border-primary bg-primary/10 text-foreground"
              : "border-border text-muted-foreground hover:border-primary/50 hover:bg-accent"
          )}>
          {role.icon}
          <span className="text-sm font-semibold">{role.label}</span>
          <span className="text-xs">{role.description}</span>
        </button>
      ))}
    </div>
  );
}

const Login = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "create">("signin");
  const [loading, setLoading] = useState(false);

  // Sign-in
  const [siEmail, setSiEmail] = useState("");
  const [siPassword, setSiPassword] = useState("");
  const [siError, setSiError] = useState("");

  // Create account
  const [caName, setCaName] = useState("");
  const [caEmail, setCaEmail] = useState("");
  const [caPassword, setCaPassword] = useState("");
  const [caConfirm, setCaConfirm] = useState("");
  const [caRole, setCaRole] = useState<UserRole | "">("");
  const [caError, setCaError] = useState("");
  const [caSuccess, setCaSuccess] = useState("");

  const switchMode = (m: "signin" | "create") => {
    setMode(m);
    setSiError(""); setCaError(""); setCaSuccess("");
  };

  const handleSignIn = async () => {
    setSiError("");
    if (!siEmail.trim() || !siPassword) { setSiError("Please enter your email and password."); return; }
    setLoading(true);
    const result = await apiLogin(siEmail.trim(), siPassword);
    setLoading(false);
    if (!result.ok) { setSiError(result.error!); return; }
    navigate("/");
  };

  const handleCreate = async () => {
    setCaError(""); setCaSuccess("");
    if (!caName.trim()) { setCaError("Name is required."); return; }
    if (!caEmail.trim() || !caEmail.includes("@")) { setCaError("Valid email is required."); return; }
    if (caPassword.length < 6) { setCaError("Password must be at least 6 characters."); return; }
    if (caPassword !== caConfirm) { setCaError("Passwords do not match."); return; }
    if (!caRole) { setCaError("Please select a role."); return; }
    setLoading(true);
    const result = await apiRegister(caName, caEmail, caRole as UserRole, caPassword);
    setLoading(false);
    if (!result.ok) { setCaError(result.error!); return; }
    // apiRegister sets the user — go straight to app
    navigate("/");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
            <Activity className="h-8 w-8 text-destructive" />
          </div>
          <CardTitle className="text-2xl font-bold">Emergency Triage</CardTitle>
          <CardDescription className="text-base">
            {mode === "signin" ? "Sign in to access the triage system" : "Create a new account"}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Tab toggle */}
          <div className="flex rounded-lg border p-1 gap-1">
            {(["signin", "create"] as const).map((m) => (
              <button key={m} type="button" onClick={() => switchMode(m)}
                className={cn(
                  "flex-1 rounded-md py-2 text-sm font-semibold transition-colors",
                  mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                )}>
                {m === "signin" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {/* Sign In */}
          {mode === "signin" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="si-email" className="text-base">Email</Label>
                <Input id="si-email" type="email" placeholder="you@hospital.com" className="h-12 text-base"
                  value={siEmail} onChange={(e) => setSiEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSignIn()} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="si-password" className="text-base">Password</Label>
                <Input id="si-password" type="password" placeholder="••••••••" className="h-12 text-base"
                  value={siPassword} onChange={(e) => setSiPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSignIn()} />
              </div>
              {siError && <p className="text-sm text-destructive">{siError}</p>}
              <Button onClick={handleSignIn} disabled={loading} className="h-14 w-full text-lg font-bold" size="lg">
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign In"}
              </Button>
            </div>
          )}

          {/* Create Account */}
          {mode === "create" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ca-name" className="text-base">Full Name</Label>
                <Input id="ca-name" placeholder="e.g. Dr. Smith" className="h-12 text-base"
                  value={caName} onChange={(e) => setCaName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ca-email" className="text-base">Email</Label>
                <Input id="ca-email" type="email" placeholder="you@hospital.com" className="h-12 text-base"
                  value={caEmail} onChange={(e) => setCaEmail(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ca-password" className="text-base">Password</Label>
                <Input id="ca-password" type="password" placeholder="Min. 6 characters" className="h-12 text-base"
                  value={caPassword} onChange={(e) => setCaPassword(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ca-confirm" className="text-base">Confirm Password</Label>
                <Input id="ca-confirm" type="password" placeholder="Re-enter password" className="h-12 text-base"
                  value={caConfirm} onChange={(e) => setCaConfirm(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()} />
              </div>
              <div className="space-y-2">
                <Label className="text-base">Select Role</Label>
                <RoleGrid selected={caRole} onSelect={setCaRole} />
              </div>
              {caError && <p className="text-sm text-destructive">{caError}</p>}
              {caSuccess && <p className="text-sm text-green-500">{caSuccess}</p>}
              <Button onClick={handleCreate} disabled={loading} className="h-14 w-full text-lg font-bold" size="lg">
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Create Account"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
};

export default Login;
