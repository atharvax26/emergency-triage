import { Link, useLocation } from "react-router-dom";
import { Activity } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Intake" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/audit", label: "Audit Log" },
];

export function NavBar() {
  const { pathname } = useLocation();

  return (
    <header className="sticky top-0 z-50 border-b bg-card">
      <nav className="container flex h-16 items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Activity className="h-7 w-7 text-severity-critical" />
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
        </div>
      </nav>
    </header>
  );
}
