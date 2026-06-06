import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/use-theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme" className="h-12 w-12">
      {theme === "dark" ? <Sun className="h-6 w-6" /> : <Moon className="h-6 w-6" />}
    </Button>
  );
}
