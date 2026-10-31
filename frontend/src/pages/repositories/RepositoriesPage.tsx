import React from "react";
import { GitBranch } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export const RepositoriesPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Connected Repositories
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage monitored GitHub repositories, default branches, and sync checkpoints.
        </p>
      </div>

      <EmptyState
        icon={GitBranch}
        title="No Repositories Connected Yet"
        description="Connect your GitHub App installation in Phase 2 to select repositories for commit activity, PR flow, and review turnaround monitoring."
        badge="Phase 2 Feature"
        actionText="Configure Integration"
        onAction={() => window.location.assign("/integrations")}
      />
    </div>
  );
};
