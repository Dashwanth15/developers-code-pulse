import React from "react";
import { Moon, Sun, Menu, Activity, ShieldCheck } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border bg-card/80 px-4 md:px-6 backdrop-blur transition-all">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-secondary md:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-md bg-secondary/80 px-2.5 py-1 text-xs font-semibold text-secondary-foreground border border-border">
            <ShieldCheck className="h-3.5 w-3.5 text-primary" />
            Developers Code Pulse
          </span>
          <span className="hidden sm:inline-block text-xs text-muted-foreground">
            v0.1.0 • Standalone Intelligence
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* API Status Indicator */}
        <div className="hidden sm:flex items-center gap-2 rounded-full bg-secondary/60 px-3 py-1 text-xs font-medium text-foreground border border-border">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <Activity className="h-3 w-3 text-emerald-500" />
          <span>Core API Ready</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Toggle visual theme"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-700" />
          )}
        </button>

        {/* User Avatar Placeholder */}
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-xs border border-primary/20">
          DCP
        </div>
      </div>
    </header>
  );
};
