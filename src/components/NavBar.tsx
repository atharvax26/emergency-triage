import { Link, useLocation } from "react-router-dom";
import { Activity, LogOut } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { ConnectionStatus } from "./ConnectionStatus";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Intake" },
  { to: "/queue", label: "Queue" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/audit", label: "Audit Log" },
];

export function NavBar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();

  return (
    <>
      {/* Skip to main content link for keyboard navigation */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-primary focus:text-primary-foreground focus:px-6 focus:py-3 focus:rounded-md focus:text-lg focus:font-bold"
      >
        Skip to main content
      </a>
      
      <header className="sticky top-0 z-50 border-b bg-card">
        <nav className="container flex h-14 items-center justify-between gap-2 px-3 sm:px-6 sm:h-16 sm:gap-8" role="navigation" aria-label="Main navigation">
          <div className="flex items-center gap-2 shrink-0">
            <Activity className="h-5 w-5 sm:h-7 sm:w-7 text-destructive" aria-hidden="true" />
            <span className="hidden sm:inline text-xl font-bold tracking-tight">Emergency Triage</span>
          </div>

          <div className="flex items-center gap-0.5 sm:gap-1 overflow-x-auto scrollbar-none">
            {links.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className={cn(
                  "rounded-md px-2 py-1.5 text-xs sm:px-4 sm:py-2 sm:text-base font-medium whitespace-nowrap",
                  pathname === l.to
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
                aria-current={pathname === l.to ? "page" : undefined}
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-1 sm:gap-2 shrink-0">
            <span className="hidden lg:flex"><ConnectionStatus /></span>
            <ThemeToggle />
            {user && (
              <div className="flex items-center gap-1 sm:gap-2">
                <Badge variant="outline" className="text-xs capitalize hidden sm:inline-flex">
                  {user.role}
                </Badge>
                <Button variant="ghost" size="icon" onClick={logout} title="Logout" aria-label="Logout">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </nav>
      </header>
    </>
  );
}
