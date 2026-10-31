import React from "react";
import { Gauge } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const DoraPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          DORA Delivery Metrics
        </h1>
        <p className="text-sm text-muted-foreground">
          Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Restore.
        </p>
      </div>

      <EmptyState
        icon={Gauge}
        title="DORA Telemetry Awaiting Deployment Sources"
        description="DCP strictly requires actual deployment and incident data to compute DORA metrics. In Phase 7, connect GitHub Actions workflows or deployment webhooks for honest delivery analytics."
        badge="Phase 7 Feature"
      />
    </div>
  );
};
