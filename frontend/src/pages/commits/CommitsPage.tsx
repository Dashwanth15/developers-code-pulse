import React from "react";
import { GitCommit } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const CommitsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Commit Intelligence
        </h1>
        <p className="text-sm text-muted-foreground">
          Observe Git commit volume, cadence, and active developer participation trends.
        </p>
      </div>

      <EmptyState
        icon={GitCommit}
        title="Commit Ingestion Unconfigured"
        description="Commit telemetry will be captured automatically via GitHub push webhooks and backfilled upon repository connection in Phase 3."
        badge="Phase 3 Feature"
      />
    </div>
  );
};
