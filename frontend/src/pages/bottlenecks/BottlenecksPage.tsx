import React from "react";
import { AlertTriangle } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const BottlenecksPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Bottleneck Detection Radar
          </h1>
          <span className="rounded-md bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-500">
            Rules Engine
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          Deterministic detection of review delays, stale PRs, queue saturation, and workload concentration.
        </p>
      </div>

      <EmptyState
        icon={AlertTriangle}
        title="Zero Bottlenecks Detected"
        description="The deterministic rules engine will evaluate your repositories against 6 core friction rules (BOT-01 through BOT-06) as events arrive in Phase 6."
        badge="Phase 6 Signature Engine"
      />
    </div>
  );
};
