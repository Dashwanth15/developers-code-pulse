import React from "react";
import { FileText } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const ReportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Engineering Reports
        </h1>
        <p className="text-sm text-muted-foreground">
          Export automated weekly retrospectives and historical executive summaries in PDF, CSV, and JSON.
        </p>
      </div>

      <EmptyState
        icon={FileText}
        title="No Reports Generated Yet"
        description="Scheduled weekly retrospectives and on-demand report exports will be compiled via the Celery reporting worker starting in Phase 8."
        badge="Phase 8 Feature"
      />
    </div>
  );
};
