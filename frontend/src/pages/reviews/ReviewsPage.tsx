import React from "react";
import { Eye } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const ReviewsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Review Intelligence
          </h1>
          <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
            Signature Feature
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          Time to First Review (TTFR), approval turnarounds, review rounds, and reviewer workload distribution.
        </p>
      </div>

      <EmptyState
        icon={Eye}
        title="Review Intelligence Pipeline Ready"
        description="Review metrics, percentile calculations (P50, P75, P90), and pending review queues will activate upon review webhook ingestion in Phase 5."
        badge="Phase 5 Signature Feature"
      />
    </div>
  );
};
