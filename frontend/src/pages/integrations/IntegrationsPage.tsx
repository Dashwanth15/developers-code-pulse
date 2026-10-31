import React from "react";
import { Boxes, Github, CheckCircle2 } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const IntegrationsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Platform Integrations
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage GitHub App connections, webhooks, and third-party delivery pipelines.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* GitHub App Integration Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foreground text-background">
                  <Github className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">GitHub App</h3>
                  <p className="text-xs text-muted-foreground">Primary source of event telemetry</p>
                </div>
              </div>
              <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground border border-border">
                Phase 2
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">
              Installs across your GitHub organization with least-privilege read-only permissions for PRs, commits, reviews, and Actions.
            </p>
            <div className="space-y-1.5 text-xs text-muted-foreground mb-6">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span>HMAC-SHA256 Cryptographic Verification</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span>Zero write-access to code or pull requests</span>
              </div>
            </div>
          </div>
          <button
            disabled
            className="w-full inline-flex items-center justify-center rounded-lg bg-secondary px-4 py-2 text-xs font-medium text-muted-foreground cursor-not-allowed border border-border"
          >
            Integration Opens in Phase 2
          </button>
        </div>

        {/* GitHub Actions Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Boxes className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">GitHub Actions CI/CD</h3>
                  <p className="text-xs text-muted-foreground">Workflow run & deployment telemetry</p>
                </div>
              </div>
              <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground border border-border">
                Phase 7
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">
              Collects build durations and production deployment events to calculate accurate DORA metrics.
            </p>
          </div>
          <button
            disabled
            className="w-full inline-flex items-center justify-center rounded-lg bg-secondary px-4 py-2 text-xs font-medium text-muted-foreground cursor-not-allowed border border-border"
          >
            Integration Opens in Phase 7
          </button>
        </div>
      </div>

      <EmptyState
        icon={Boxes}
        title="Integration Engine Ready"
        description="The backend webhook ingestion router and signature verification services are pre-configured to receive events upon registering the GitHub App credentials."
        badge="Ready for Phase 2"
      />
    </div>
  );
};
