import React from "react";
import { Users } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const TeamInsightsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Team Insights & Collaboration
        </h1>
        <p className="text-sm text-muted-foreground">
          Team throughput, cross-repository collaboration patterns, and healthy workload balancing.
        </p>
      </div>

      <EmptyState
        icon={Users}
        title="Team Intelligence Pending Setup"
        description="Team-level review networks and throughput trends will be computed in Phase 7 with strict adherence to our anti-surveillance privacy charter."
        badge="Phase 7 Feature"
      />
    </div>
  );
};
