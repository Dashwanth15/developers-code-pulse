import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Github,
  CheckCircle2,
  RefreshCw,
  Plus,
  GitBranch,
  Lock,
  Globe,
  Radio,
  ExternalLink,
  Shield,
  Loader2,
} from "lucide-react";
import { api, DiscoveredRepo } from "@/services/api";

export const IntegrationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [connectSuccessMsg, setConnectSuccessMsg] = useState<string | null>(null);

  // Discover GitHub repositories
  const {
    data: discoveredRepos,
    isLoading: isDiscovering,
    refetch: refetchDiscovery,
    isRefetching,
  } = useQuery<DiscoveredRepo[]>({
    queryKey: ["github-discovered-repos"],
    queryFn: () => api.github.discover(),
    retry: 1,
  });

  // Connect repository mutation
  const connectMutation = useMutation({
    mutationFn: (repo: DiscoveredRepo) =>
      api.repositories.connect({
        github_repo_id: repo.github_repo_id,
        name: repo.name,
        full_name: repo.full_name,
        default_branch: repo.default_branch,
        is_private: repo.is_private,
        primary_language: repo.primary_language,
      }),
    onSuccess: (data) => {
      setConnectSuccessMsg(`Successfully connected ${data.name} to monitored repositories!`);
      queryClient.invalidateQueries({ queryKey: ["github-discovered-repos"] });
      queryClient.invalidateQueries({ queryKey: ["connected-repositories"] });
      setTimeout(() => setConnectSuccessMsg(null), 4000);
    },
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Platform Integrations
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage GitHub connections, repository discovery, and webhook telemetry ingestion pipelines.
        </p>
      </div>

      {connectSuccessMsg && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{connectSuccessMsg}</span>
        </div>
      )}

      {/* Primary Integration Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* GitHub Integration Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-foreground text-background shadow-sm">
                  <Github className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">GitHub Integration</h3>
                  <p className="text-xs text-muted-foreground">Fine-grained API & Webhook Ingestion</p>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Active • Dashwanth15
              </span>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed mb-4">
              Connected with cryptographic HMAC-SHA256 verification. Grants least-privilege read access to pull requests, commit streams, reviews, and workflow runs.
            </p>

            <div className="space-y-2 text-xs text-muted-foreground mb-6">
              <div className="flex items-center gap-2">
                <Shield className="h-3.5 w-3.5 text-primary" />
                <span>HMAC-SHA256 Timing-Safe Signature Validation</span>
              </div>
              <div className="flex items-center gap-2">
                <Radio className="h-3.5 w-3.5 text-primary" />
                <span>Idempotent Delivery Deduplication (`X-GitHub-Delivery`)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span>Zero write-access to codebase or repositories</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-3 border-t border-border/60">
            <button
              onClick={() => refetchDiscovery()}
              disabled={isDiscovering || isRefetching}
              className="inline-flex items-center gap-2 rounded-lg bg-primary py-2 px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 transition-all shadow-sm"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isDiscovering || isRefetching ? "animate-spin" : ""}`} />
              <span>{isDiscovering || isRefetching ? "Discovering..." : "Scan Repositories"}</span>
            </button>
          </div>
        </div>

        {/* Webhook Configuration Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Radio className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">Webhook Endpoint</h3>
                  <p className="text-xs text-muted-foreground">High-throughput asynchronous ingest</p>
                </div>
              </div>
              <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground border border-border">
                Ready
              </span>
            </div>

            <div className="space-y-3 mb-4">
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground">Payload URL</span>
                <div className="rounded-md bg-secondary/80 px-3 py-1.5 font-mono text-xs text-foreground border border-border select-all">
                  /api/v1/integrations/github/webhooks
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground">Content type</span>
                <div className="rounded-md bg-secondary/80 px-3 py-1.5 font-mono text-xs text-foreground border border-border">
                  application/json
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground">Supported Events</span>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {["push", "pull_request", "pull_request_review", "check_run"].map((evt) => (
                    <span
                      key={evt}
                      className="rounded bg-secondary px-2 py-0.5 text-[10px] font-mono font-medium text-secondary-foreground border border-border"
                    >
                      {evt}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-muted-foreground">
            Webhooks are ingested with a sub-50ms acknowledgement and enqueued for Celery worker processing.
          </div>
        </div>
      </div>

      {/* Discovered Repositories Section */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h3 className="text-base font-semibold text-foreground">Discovered GitHub Repositories</h3>
            <p className="text-xs text-muted-foreground">
              Select repositories from your authorized GitHub account to connect for engineering intelligence.
            </p>
          </div>
          <button
            onClick={() => refetchDiscovery()}
            disabled={isDiscovering || isRefetching}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary transition-all"
          >
            <RefreshCw className={`h-3 w-3 ${isDiscovering || isRefetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {isDiscovering ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
            <p className="text-sm font-medium text-foreground">Discovering authorized repositories...</p>
            <p className="text-xs text-muted-foreground">Connecting to GitHub REST API with configured credentials.</p>
          </div>
        ) : discoveredRepos && discoveredRepos.length > 0 ? (
          <div className="divide-y divide-border">
            {discoveredRepos.map((repo) => (
              <div
                key={repo.github_repo_id}
                className="flex items-center justify-between px-6 py-4 hover:bg-muted/30 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-foreground">{repo.name}</span>
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
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <GitBranch className="h-3 w-3" /> {repo.default_branch}
                    </span>
                    <span>•</span>
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 hover:underline text-muted-foreground"
                    >
                      <span>{repo.full_name}</span>
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </div>
                </div>

                <div>
                  {repo.is_connected ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Connected
                    </span>
                  ) : (
                    <button
                      onClick={() => connectMutation.mutate(repo)}
                      disabled={connectMutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 transition-all shadow-sm"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>Connect</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center px-4">
            <Github className="mx-auto h-8 w-8 text-muted-foreground mb-3 opacity-60" />
            <p className="text-sm font-medium text-foreground">No repositories returned</p>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
              Verify your GitHub Personal Access Token or GitHub App installation has repository read permissions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
