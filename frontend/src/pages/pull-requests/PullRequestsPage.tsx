import React from "react";
import { GitPullRequest } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const PullRequestsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Pull Request Analytics
        </h1>
        <p className="text-sm text-muted-foreground">
          Track PR lifecycle, cycle times, merge latencies, and PR size distribution.
        </p>
      </div>

      <EmptyState
        icon={GitPullRequest}
        title="Pull Request Analytics Awaiting Data"
        description="PR creation, review, and merge events will be processed by the Celery normalizer worker and analytics engine starting in Phase 4."
        badge="Phase 4 Feature"
      />
    </div>
  );
};
