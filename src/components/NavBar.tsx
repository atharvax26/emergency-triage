import { Link, useLocation } from "react-router-dom";
import { Activity, LogOut } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Intake" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/audit", label: "Audit Log" },
];

export function NavBar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b bg-card">
      <nav className="container flex h-16 items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Activity className="h-7 w-7 text-destructive" />
          <span className="text-xl font-bold tracking-tight">Emergency Triage</span>
        </div>

        <div className="flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={cn(
                "rounded-md px-4 py-2 text-base font-medium transition-colors",
                pathname === l.to
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {l.label}
            </Link>
          ))}
          <ThemeToggle />
          {user && (
            <div className="ml-2 flex items-center gap-2">
              <Badge variant="outline" className="text-xs capitalize">
                {user.role}
              </Badge>
              <Button variant="ghost" size="icon" onClick={logout} title="Logout">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
