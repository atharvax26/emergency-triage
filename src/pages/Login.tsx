import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Stethoscope, HeartPulse, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useAuth, type UserRole } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const roles: { value: UserRole; label: string; icon: React.ReactNode; description: string }[] = [
  {
    value: "nurse",
    label: "Nurse",
    icon: <HeartPulse className="h-8 w-8" />,
    description: "Triage intake & patient assessment",
  },
  {
    value: "doctor",
    label: "Doctor",
    icon: <Stethoscope className="h-8 w-8" />,
    description: "Full dashboard & override access",
  },
  {
    value: "admin",
    label: "Admin",
    icon: <Shield className="h-8 w-8" />,
    description: "System management & audit logs",
  },
];

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [name, setName] = useState("");
  const [selectedRole, setSelectedRole] = useState<UserRole | "">("");

  const canSubmit = name.trim().length > 0 && selectedRole !== "";

  const handleLogin = () => {
    if (!canSubmit) return;
    login(name.trim(), selectedRole as UserRole);
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
            Sign in to access the triage system
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="login-name" className="text-base">
              Your Name
            </Label>
            <Input
              id="login-name"
              placeholder="e.g. Dr. Smith"
              className="h-12 text-base"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            />
          </div>

          {/* Role selection */}
          <div className="space-y-2">
            <Label className="text-base">Select Role</Label>
            <div className="grid grid-cols-3 gap-3">
              {roles.map((role) => (
                <button
                  key={role.value}
                  type="button"
                  onClick={() => setSelectedRole(role.value)}
                  className={cn(
                    "flex flex-col items-center gap-2 rounded-lg border-2 p-4 text-center",
                    selectedRole === role.value
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border text-muted-foreground hover:border-primary/50 hover:bg-accent"
                  )}
                >
                  {role.icon}
                  <span className="text-sm font-semibold">{role.label}</span>
                  <span className="text-xs">{role.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <Button
            onClick={handleLogin}
            disabled={!canSubmit}
            className="h-14 w-full text-lg font-bold"
            size="lg"
          >
            Sign In
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            This is a mock login — no real authentication is performed.
          </p>
        </CardContent>
      </Card>
    </main>
  );
};

export default Login;
