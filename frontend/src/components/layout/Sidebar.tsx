import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  GitBranch,
  GitCommit,
  GitPullRequest,
  Eye,
  Users,
  AlertTriangle,
  Gauge,
  FileText,
  Sparkles,
  Boxes,
  Settings,
  Activity,
  X,
} from "lucide-react";
import { cn } from "@/utils/cn";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  title: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "OVERVIEW",
    items: [
      { title: "Dashboard", path: "/", icon: LayoutDashboard },
    ],
  },
  {
    label: "DEVELOPMENT INTELLIGENCE",
    items: [
      { title: "Repositories", path: "/repositories", icon: GitBranch },
      { title: "Commit Analytics", path: "/commits", icon: GitCommit },
      { title: "Pull Request Analytics", path: "/pull-requests", icon: GitPullRequest },
      { title: "Review Intelligence", path: "/reviews", icon: Eye, badge: "Signature" },
    ],
  },
  {
    label: "TEAM INTELLIGENCE",
    items: [
      { title: "Team Insights", path: "/team-insights", icon: Users },
      { title: "Bottleneck Detection", path: "/bottlenecks", icon: AlertTriangle, badge: "Engine" },
    ],
  },
  {
    label: "DELIVERY INTELLIGENCE",
    items: [
      { title: "DORA Metrics", path: "/dora", icon: Gauge },
    ],
  },
  {
    label: "REPORTING",
    items: [
      { title: "Engineering Reports", path: "/reports", icon: FileText },
      { title: "AI Insights", path: "/insights", icon: Sparkles, badge: "AI" },
    ],
  },
  {
    label: "MANAGEMENT",
    items: [
      { title: "Integrations", path: "/integrations", icon: Boxes },
      { title: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card transition-transform duration-200 ease-in-out md:static md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-border px-5">
          <NavLink to="/" className="flex items-center gap-2.5 font-bold text-foreground">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Activity className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-extrabold tracking-tight leading-none">
                Developers Code Pulse
              </span>
              <span className="text-[10px] text-muted-foreground font-normal mt-0.5 tracking-wider uppercase">
                Engineering Intel
              </span>
            </div>
          </NavLink>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary md:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navGroups.map((group) => (
            <div key={group.label} className="space-y-1">
              <h4 className="px-3 text-[10px] font-semibold text-muted-foreground tracking-wider uppercase">
                {group.label}
              </h4>
              <nav className="space-y-0.5 pt-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => {
                      if (window.innerWidth < 768) onClose();
                    }}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <div className="flex items-center gap-3">
                          <item.icon
                            className={cn(
                              "h-4 w-4 shrink-0 transition-colors",
                              isActive
                                ? "text-primary-foreground"
                                : "text-muted-foreground group-hover:text-foreground"
                            )}
                          />
                          <span>{item.title}</span>
                        </div>
                        {item.badge && (
                          <span
                            className={cn(
                              "text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded",
                              isActive
                                ? "bg-primary-foreground/20 text-primary-foreground"
                                : "bg-primary/10 text-primary"
                            )}
                          >
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>
            </div>
          ))}
        </div>

        {/* Footer Tagline */}
        <div className="border-t border-border p-4 bg-secondary/30">
          <p className="text-[11px] text-muted-foreground font-medium italic text-center">
            "Understand your team's workflow. Build better software. Ship faster together."
          </p>
        </div>
      </aside>
    </>
  );
};
