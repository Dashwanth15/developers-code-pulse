import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitPullRequest,
  GitMerge,
  Clock,
  Zap,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  ArrowRight,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  api,
  ConnectedRepository,
  PRAnalyticsResponse,
  PullRequestListResponse,
} from "@/services/api";
import { EmptyState } from "@/components/common/EmptyState";

export const PullRequestsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [timeWindow, setTimeWindow] = useState<string>("30d");
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  // 1. Fetch monitored repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // 2. Fetch PR Analytics
  const repoIds = selectedRepoId !== "all" ? [selectedRepoId] : undefined;
  const {
    data: analytics,
    isLoading: isAnalyticsLoading,
    refetch: refetchAnalytics,
    isRefetching: isAnalyticsRefetching,
  } = useQuery<PRAnalyticsResponse>({
    queryKey: ["pr-analytics", timeWindow, selectedRepoId],
    queryFn: () =>
      api.analytics.getPullRequests({
        time_window: timeWindow,
        repository_ids: repoIds,
      }),
  });

  // 3. Fetch PR Listings
  const {
    data: prList,
    isLoading: isListLoading,
    refetch: refetchList,
  } = useQuery<PullRequestListResponse>({
    queryKey: ["pull-requests-list", selectedRepoId, stateFilter],
    queryFn: () =>
      api.pullRequests.list({
        repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
        state: stateFilter !== "all" ? stateFilter : undefined,
        page: 1,
        size: 20,
      }),
  });

  // 4. PR Sync Mutation
  const syncMutation = useMutation({
    mutationFn: (repoId: string) => api.repositories.syncPullRequests(repoId),
    onSuccess: (data) => {
      setSyncFeedback(`Successfully synchronized ${data.synced_pull_requests} pull requests from GitHub.`);
      queryClient.invalidateQueries({ queryKey: ["pr-analytics"] });
      queryClient.invalidateQueries({ queryKey: ["pull-requests-list"] });
      setTimeout(() => setSyncFeedback(null), 5000);
    },
    onError: (err: Error) => {
      setSyncFeedback(`Sync failed: ${err.message}`);
      setTimeout(() => setSyncFeedback(null), 5000);
    },
  });

  const handleSync = () => {
    if (selectedRepoId !== "all") {
      syncMutation.mutate(selectedRepoId);
    } else if (repositories && repositories.length > 0) {
      syncMutation.mutate(repositories[0].id);
    }
  };

  const handleRefresh = () => {
    refetchAnalytics();
    refetchList();
  };

  // SVG Chart Calculations
  const trend = analytics?.cadence_trend || [];
  const maxDayCount = trend.reduce(
    (max, item) => Math.max(max, item.opened + item.merged + item.closed),
    0
  ) || 1;

  const summary = analytics?.summary;
  const sizeDist = analytics?.size_distribution;

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Pull Request Analytics
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="w-3 h-3" />
              Flow & Throughput
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            End-to-end pull request lifecycle velocity, review latencies, and size distributions.
          </p>
        </div>

        {/* Global Filter Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Repository Selector */}
          <select
            id="pr-repo-filter"
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="text-xs font-medium rounded-lg bg-card border border-border px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-sm"
          >
            <option value="all">All Monitored Repositories</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          {/* Time Window Switcher */}
          <div className="flex items-center p-0.5 rounded-lg bg-muted border border-border">
            {["7d", "14d", "30d", "90d"].map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setTimeWindow(w)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  timeWindow === w
                    ? "bg-card text-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Sync & Refresh Actions */}
          <button
            type="button"
            id="sync-prs-btn"
            onClick={handleSync}
            disabled={syncMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50"
          >
            {syncMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <GitPullRequest className="w-3.5 h-3.5" />
            )}
            Sync PRs
          </button>

          <button
            type="button"
            id="refresh-prs-btn"
            onClick={handleRefresh}
            disabled={isAnalyticsRefetching}
            className="p-2 text-muted-foreground hover:text-foreground rounded-lg border border-border bg-card shadow-sm transition-all"
            title="Refresh analytics"
          >
            <RefreshCw className={`w-4 h-4 ${isAnalyticsRefetching ? "animate-spin text-primary" : ""}`} />
          </button>
        </div>
      </div>

      {/* Sync Status Banner */}
      {syncFeedback && (
        <div className="flex items-center gap-2 p-3 text-xs rounded-xl bg-primary/10 border border-primary/20 text-primary">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{syncFeedback}</span>
        </div>
      )}

      {/* Anti-Surveillance Manifesto Commitment Banner */}
      <div className="p-4 rounded-xl border border-primary/20 bg-gradient-to-r from-primary/5 via-accent/5 to-transparent flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <h2 className="text-xs font-bold text-foreground tracking-wide uppercase">
            Anti-Surveillance Commitment
          </h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            DCP measures aggregate engineering flow, cycle efficiency, and review responsiveness. It strictly rejects individual developer speed benchmarking, merge quotas, or surveillance telemetry.
          </p>
        </div>
      </div>

      {/* 4 Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Merge Rate */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">PR Merge Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <GitMerge className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {summary ? `${summary.merge_rate_percentage}%` : "--"}
            </span>
            <span className="text-xs text-muted-foreground">
              {summary?.total_prs_merged || 0} merged / {summary?.total_prs_closed_unmerged || 0} rejected
            </span>
          </div>
          <div className="mt-3 w-full bg-muted rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(summary?.merge_rate_percentage || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Card 2: Median Merge Time (T_merge) */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Median Merge Time (P50)</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {summary?.median_merge_time_hours != null
                ? `${summary.median_merge_time_hours}h`
                : "--"}
            </span>
            {summary?.p75_merge_time_hours != null && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-500">
                P75: {summary.p75_merge_time_hours}h
              </span>
            )}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Duration from review-ready state to successful branch merge.
          </p>
        </div>

        {/* Card 3: Median Cycle Time (T_cycle) */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Median Cycle Time</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {summary?.median_cycle_time_hours != null
                ? `${summary.median_cycle_time_hours}h`
                : "--"}
            </span>
            <span className="text-xs text-muted-foreground">first commit to merge</span>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Measures end-to-end latency including active coding and review rework.
          </p>
        </div>

        {/* Card 4: Currently Active PRs */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Currently Open</span>
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <GitPullRequest className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {summary?.currently_open_prs ?? "--"}
            </span>
            <span className="text-xs text-muted-foreground">active in review queue</span>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Total non-draft PRs awaiting approval, changes, or final merge.
          </p>
        </div>
      </div>

      {/* PR Throughput & Cadence Timeline (Interactive SVG) */}
      <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-foreground">PR Throughput & Lifecycle Timeline</h2>
            <p className="text-xs text-muted-foreground">
              Daily volume of pull requests opened, merged, and closed unmerged across the selected window.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-muted-foreground">Opened</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-muted-foreground">Merged</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-rose-500" />
              <span className="text-muted-foreground">Closed Unmerged</span>
            </div>
          </div>
        </div>

        {isAnalyticsLoading ? (
          <div className="h-56 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : trend.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-muted-foreground text-xs">
            <AlertCircle className="w-6 h-6 mb-2 opacity-50" />
            <span>No pull request activity recorded in this time window.</span>
          </div>
        ) : (
          <div className="space-y-2">
            {/* SVG Interactive Stacked Timeline */}
            <div className="w-full overflow-x-auto">
              <svg className="w-full h-48 min-w-[500px]" preserveAspectRatio="none" viewBox="0 0 800 160">
                {trend.map((point, idx) => {
                  const x = (idx / Math.max(trend.length - 1, 1)) * 740 + 30;
                  const openedH = (point.opened / maxDayCount) * 110;
                  const mergedH = (point.merged / maxDayCount) * 110;
                  const closedH = (point.closed / maxDayCount) * 110;
                  const barW = Math.max(700 / trend.length - 4, 6);

                  return (
                    <g key={point.date} className="group cursor-pointer">
                      {/* Grid guideline */}
                      <line
                        x1={x}
                        y1="130"
                        x2={x}
                        y2="20"
                        stroke="currentColor"
                        className="text-border/20 group-hover:text-primary/40 transition-colors"
                        strokeDasharray="2 2"
                      />

                      {/* Stacked Bars: Opened (blue), Merged (emerald), Closed (rose) */}
                      {point.opened > 0 && (
                        <rect
                          x={x - barW / 2}
                          y={130 - openedH}
                          width={barW}
                          height={openedH}
                          className="fill-blue-500/80 hover:fill-blue-400 transition-colors"
                          rx="2"
                        />
                      )}
                      {point.merged > 0 && (
                        <rect
                          x={x - barW / 2}
                          y={130 - openedH - mergedH}
                          width={barW}
                          height={mergedH}
                          className="fill-emerald-500/90 hover:fill-emerald-400 transition-colors"
                          rx="2"
                        />
                      )}
                      {point.closed > 0 && (
                        <rect
                          x={x - barW / 2}
                          y={130 - openedH - mergedH - closedH}
                          width={barW}
                          height={closedH}
                          className="fill-rose-500/80 hover:fill-rose-400 transition-colors"
                          rx="2"
                        />
                      )}

                      {/* Hover Tooltip Label */}
                      <title>{`${point.date}: ${point.opened} Opened, ${point.merged} Merged, ${point.closed} Closed`}</title>
                    </g>
                  );
                })}

                {/* Baseline Axis */}
                <line x1="20" y1="130" x2="780" y2="130" stroke="currentColor" className="text-border" />
              </svg>
            </div>

            {/* Date range footer */}
            <div className="flex justify-between text-[11px] text-muted-foreground px-4">
              <span>{analytics?.start_date}</span>
              <span>{analytics?.end_date}</span>
            </div>
          </div>
        )}
      </div>

      {/* PR Size Distribution Section */}
      <div className="space-y-3">
        <div>
          <h2 className="text-sm font-bold text-foreground">PR Size Distribution & Review Latency</h2>
          <p className="text-xs text-muted-foreground">
            Smaller pull requests merge significantly faster and face fewer merge conflicts or review deadlocks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Small PRs (< 100 lines) */}
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-500 px-2 py-0.5 rounded-full bg-emerald-500/10">
                Small (under 100 lines)
              </span>
              <Layers className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-2xl font-extrabold text-foreground">
                  {sizeDist?.small_under_100_lines.count ?? 0}
                </span>
                <span className="text-xs text-muted-foreground ml-1">PRs</span>
              </div>
              <div className="text-right">
                <span className="text-xs text-muted-foreground block">Avg Merge Time</span>
                <span className="text-sm font-bold text-foreground">
                  {sizeDist?.small_under_100_lines.avg_merge_hours != null
                    ? `${sizeDist.small_under_100_lines.avg_merge_hours}h`
                    : "--"}
                </span>
              </div>
            </div>
            <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
              Optimal review efficiency & lowest cognitive load.
            </p>
          </div>

          {/* Medium PRs (100 - 500 lines) */}
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-500 px-2 py-0.5 rounded-full bg-blue-500/10">
                Medium (100 to 500 lines)
              </span>
              <Layers className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-2xl font-extrabold text-foreground">
                  {sizeDist?.medium_100_to_500_lines.count ?? 0}
                </span>
                <span className="text-xs text-muted-foreground ml-1">PRs</span>
              </div>
              <div className="text-right">
                <span className="text-xs text-muted-foreground block">Avg Merge Time</span>
                <span className="text-sm font-bold text-foreground">
                  {sizeDist?.medium_100_to_500_lines.avg_merge_hours != null
                    ? `${sizeDist.medium_100_to_500_lines.avg_merge_hours}h`
                    : "--"}
                </span>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Standard feature scope; manageable review turnaround.
            </p>
          </div>

          {/* Large PRs (> 500 lines) */}
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-500 px-2 py-0.5 rounded-full bg-amber-500/10">
                Large (over 500 lines)
              </span>
              <Layers className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-2xl font-extrabold text-foreground">
                  {sizeDist?.large_over_500_lines.count ?? 0}
                </span>
                <span className="text-xs text-muted-foreground ml-1">PRs</span>
              </div>
              <div className="text-right">
                <span className="text-xs text-muted-foreground block">Avg Merge Time</span>
                <span className="text-sm font-bold text-foreground">
                  {sizeDist?.large_over_500_lines.avg_merge_hours != null
                    ? `${sizeDist.large_over_500_lines.avg_merge_hours}h`
                    : "--"}
                </span>
              </div>
            </div>
            <p className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">
              High review friction risk; consider breaking into stacked PRs.
            </p>
          </div>
        </div>
      </div>

      {/* Pull Requests Collection Table */}
      <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-foreground">Monitored Pull Requests</h2>
            <p className="text-xs text-muted-foreground">
              Real-time feed of pull requests ingested from GitHub webhooks and API synchronization.
            </p>
          </div>

          {/* State Filter Buttons */}
          <div className="flex items-center p-0.5 rounded-lg bg-muted border border-border">
            {["all", "OPEN", "MERGED", "CLOSED"].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStateFilter(s)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  stateFilter === s
                    ? "bg-card text-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {s.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {isListLoading ? (
          <div className="py-12 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : !prList?.items || prList.items.length === 0 ? (
          <EmptyState
            icon={GitPullRequest}
            title="No Pull Requests Ingested Yet"
            description="Connect your repositories and trigger synchronization or open a PR in GitHub to stream live telemetry."
            badge="Phase 4 Ready"
          />
        ) : (
          <div className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {prList.items?.map((pr) => {
              const stateColor =
                pr.state === "MERGED"
                  ? "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
                  : pr.state === "OPEN"
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                  : "bg-muted text-muted-foreground border-border";

              const StateIcon =
                pr.state === "MERGED" ? GitMerge : pr.state === "OPEN" ? GitPullRequest : XCircle;

              const mergeTimeHours =
                pr.merge_time_seconds != null ? (pr.merge_time_seconds / 3600).toFixed(1) : null;

              return (
                <div
                  key={pr.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-muted/30 transition-colors"
                >
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full border ${stateColor}`}>
                        <StateIcon className="w-3 h-3" />
                        {pr.state}
                      </span>
                      <span className="text-xs font-mono font-semibold text-muted-foreground">
                        #{pr.number}
                      </span>
                      <h3 className="text-sm font-bold text-foreground truncate">
                        {pr.title}
                      </h3>
                      {pr.is_draft && (
                        <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-muted text-muted-foreground">
                          DRAFT
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {/* Author */}
                      {pr.author_login && (
                        <div className="flex items-center gap-1.5">
                          {pr.author_avatar ? (
                            <img
                              src={pr.author_avatar}
                              alt={pr.author_login}
                              className="w-4 h-4 rounded-full border border-border"
                            />
                          ) : (
                            <div className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center text-[9px] font-bold text-primary">
                              {pr.author_login[0].toUpperCase()}
                            </div>
                          )}
                          <span className="font-medium text-foreground">{pr.author_login}</span>
                        </div>
                      )}

                      {/* Branches */}
                      <div className="flex items-center gap-1 text-[11px] font-mono">
                        <span className="text-muted-foreground">{pr.source_branch}</span>
                        <ArrowRight className="w-3 h-3 text-muted-foreground/60" />
                        <span className="text-muted-foreground">{pr.target_branch}</span>
                      </div>

                      {/* Lines added / removed */}
                      <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        +{pr.additions}
                      </span>
                      <span className="text-xs font-medium text-rose-600 dark:text-rose-400">
                        -{pr.deletions}
                      </span>
                    </div>
                  </div>

                  {/* Latency Pill */}
                  <div className="flex sm:flex-col items-end justify-between sm:justify-center text-xs shrink-0">
                    {mergeTimeHours ? (
                      <div className="text-right">
                        <span className="font-bold text-foreground">{mergeTimeHours}h</span>
                        <span className="text-[10px] text-muted-foreground block">Merge Latency</span>
                      </div>
                    ) : (
                      <div className="text-right">
                        <span className="text-[11px] text-muted-foreground">
                          Created {new Date(pr.created_at_github).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
