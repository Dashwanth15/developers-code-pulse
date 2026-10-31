import React from "react";
import { Shield, Sliders } from "lucide-react";

export const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Platform Settings & Governance
        </h1>
        <p className="text-sm text-muted-foreground">
          Organization policies, role-based access control, and anti-surveillance privacy boundaries.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Anti-Surveillance Charter Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">Anti-Surveillance Commitment</h3>
              <p className="text-xs text-muted-foreground">Ethical engineering intelligence principles</p>
            </div>
          </div>
          <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
            <p>
              Developers Code Pulse is built to improve team delivery velocity and identify workflow bottlenecks, not to rank or monitor individual engineers.
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>No individual developer productivity scoring.</li>
              <li>Lines of code (LOC) are never used as a performance indicator.</li>
              <li>Review distribution indexes protect senior engineers from burnout.</li>
              <li>Transparent bottleneck detection rules traceable to stored metrics.</li>
            </ul>
          </div>
        </div>

        {/* Foundation Settings Overview */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">Organization Configuration</h3>
              <p className="text-xs text-muted-foreground">Tenant isolation & RBAC controls</p>
            </div>
          </div>
          <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
            <p>
              Multi-tenant architecture enforces strict data isolation at the organization level with four defined roles:
            </p>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <div className="rounded border border-border p-2 bg-secondary/30">
                <span className="font-semibold text-foreground">Owner:</span> Full administration & billing.
              </div>
              <div className="rounded border border-border p-2 bg-secondary/30">
                <span className="font-semibold text-foreground">Admin:</span> Repo & rule configuration.
              </div>
              <div className="rounded border border-border p-2 bg-secondary/30">
                <span className="font-semibold text-foreground">Member:</span> Full analytics & reports.
              </div>
              <div className="rounded border border-border p-2 bg-secondary/30">
                <span className="font-semibold text-foreground">Viewer:</span> Read-only dashboards.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
