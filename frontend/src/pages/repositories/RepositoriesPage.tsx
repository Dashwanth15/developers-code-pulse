import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitBranch,
  Search,
  ExternalLink,
  Lock,
  Globe,
  Radio,
  Plus,
  Loader2,
  CheckCircle,
  PauseCircle,
} from "lucide-react";
import { api, ConnectedRepository } from "@/services/api";
import { EmptyState } from "@/components/common/EmptyState";

export const RepositoriesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");

  const {
    data: repositories,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_monitored }: { id: string; is_monitored: boolean }) =>
      api.repositories.toggleMonitoring(id, is_monitored),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connected-repositories"] });
    },
  });

  const filteredRepos = (repositories || []).filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      repo.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (repo.primary_language && repo.primary_language.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const activeCount = (repositories || []).filter((r) => r.is_monitored).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Connected Repositories
          </h1>
          <p className="text-sm text-muted-foreground">
            {repositories && repositories.length > 0
              ? `${repositories.length} connected repositories • ${activeCount} active monitoring`
              : "Manage GitHub repositories, default branches, and real-time event ingestion."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/integrations"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span>Connect Repository</span>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
          <p className="text-sm font-medium text-foreground">Loading connected repositories...</p>
        </div>
      ) : !repositories || repositories.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No Repositories Connected Yet"
          description="Discover and connect repositories from your GitHub account to start ingesting commit telemetry, pull request metrics, and review turnaround."
          badge="Ready for Ingestion"
          actionText="Connect Repository"
          onAction={() => window.location.assign("/integrations")}
        />
      ) : (
        <div className="space-y-4">
          {/* Search bar */}
          <div className="flex items-center justify-between gap-4">
            <div className="relative max-w-sm flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by repository name or language..."
                className="w-full rounded-lg border border-input bg-card pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-all"
              />
            </div>

            <button
              onClick={() => refetch()}
              disabled={isRefetching}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-all"
            >
              <span>Refresh</span>
            </button>
          </div>

          {/* Repositories Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredRepos.map((repo) => (
              <div
                key={repo.id}
                className={`rounded-xl border transition-all p-5 shadow-sm flex flex-col justify-between ${
                  repo.is_monitored
                    ? "border-border bg-card hover:border-primary/40"
                    : "border-border/60 bg-muted/20 opacity-80"
                }`}
              >
                <div>
                  {/* Top tags */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                      <GitBranch className="h-3.5 w-3.5 text-primary" />
                      <span>{repo.default_branch}</span>
                    </span>

                    <div className="flex items-center gap-1.5">
                      {repo.is_private ? (
                        <span className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
                          <Lock className="h-2.5 w-2.5" /> Private
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
                          <Globe className="h-2.5 w-2.5" /> Public
                        </span>
                      )}

                      {repo.primary_language && (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                          {repo.primary_language}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Name and link */}
                  <h3 className="font-semibold text-base text-foreground mb-1 flex items-center justify-between">
                    <span className="truncate">{repo.name}</span>
                    <a
                      href={`https://github.com/${repo.full_name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground shrink-0 ml-2"
                      aria-label="View on GitHub"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </h3>
                  <p className="text-xs text-muted-foreground font-mono truncate mb-4">
                    {repo.full_name}
                  </p>
                </div>

                {/* Footer Controls */}
                <div className="pt-4 border-t border-border flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    {repo.is_monitored ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-500">
                        <CheckCircle className="h-3.5 w-3.5" /> Monitored
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
                        <PauseCircle className="h-3.5 w-3.5" /> Paused
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() =>
                      toggleMutation.mutate({
                        id: repo.id,
                        is_monitored: !repo.is_monitored,
                      })
                    }
                    disabled={toggleMutation.isPending}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                      repo.is_monitored
                        ? "bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border"
                        : "bg-primary text-primary-foreground hover:bg-primary/90"
                    }`}
                  >
                    <Radio className="h-3 w-3" />
                    <span>{repo.is_monitored ? "Pause" : "Resume"}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
