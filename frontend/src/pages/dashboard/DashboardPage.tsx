import React from "react";
import {
  GitPullRequest,
  Clock,
  AlertTriangle,
  GitCommit,
  ArrowUpRight,
  ShieldCheck,
  Boxes,
} from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { Link } from "react-router-dom";

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Engineering Overview
          </h1>
          <p className="text-sm text-muted-foreground">
            High-level metrics and workflow intelligence across your organization.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/integrations"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow transition hover:bg-primary/90"
          >
            <Boxes className="h-3.5 w-3.5" />
            Connect GitHub
          </Link>
        </div>
      </div>

      {/* KPI Cards Placeholder Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Connected Repos</span>
            <GitPullRequest className="h-4 w-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-foreground">0</div>
          <p className="text-xs text-muted-foreground mt-1">Ready for repository configuration</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Median TTFR</span>
            <Clock className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-foreground">--</div>
          <p className="text-xs text-muted-foreground mt-1">Time to first review</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">PR Merge Time</span>
            <GitCommit className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-foreground">--</div>
          <p className="text-xs text-muted-foreground mt-1">Average creation to merge</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Bottlenecks</span>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-foreground">0</div>
          <p className="text-xs text-muted-foreground mt-1">Rules engine active</p>
        </div>
      </div>

      {/* Foundation Onboarding State */}
      <EmptyState
        icon={ShieldCheck}
        title="DCP Core Foundation Initialized"
        description="The backend API, PostgreSQL database, Redis message broker, and React dashboard shell are active. Live metrics will populate automatically upon connecting your GitHub App in Phase 2."
        badge="Phase 1 Foundation Active"
        actionText="Review Integrations"
        onAction={() => window.location.assign("/integrations")}
      />

      {/* Philosophy Banner */}
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground">Team Workflow Intelligence</h4>
            <p className="text-xs text-muted-foreground">
              DCP focuses on team cycle time, review turnarounds, and systemic bottlenecks—never individual surveillance.
            </p>
          </div>
        </div>
        <Link
          to="/settings"
          className="text-xs font-medium text-primary hover:underline flex items-center gap-1"
        >
          View Privacy Charter <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
};
