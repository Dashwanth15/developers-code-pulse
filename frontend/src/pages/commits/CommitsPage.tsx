import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitCommit,
  Calendar,
  Users,
  TrendingUp,
  RefreshCw,
  ShieldCheck,
  FolderGit2,
  FileCode,
  Loader2,
  AlertCircle,
  Plus,
} from "lucide-react";
import { api, CommitAnalyticsResponse, ConnectedRepository } from "@/services/api";
import { EmptyState } from "@/components/common/EmptyState";

const DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const CommitsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [timeWindow, setTimeWindow] = useState<string>("30d");
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  // Fetch connected repositories for filter dropdown
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // Fetch commit analytics
  const repoIds = selectedRepoId !== "all" ? [selectedRepoId] : undefined;
  const {
    data: analytics,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery<CommitAnalyticsResponse>({
    queryKey: ["commit-analytics", timeWindow, selectedRepoId],
    queryFn: () => api.analytics.getCommits({ time_window: timeWindow, repository_ids: repoIds }),
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: (repoId: string) => api.repositories.syncCommits(repoId),
    onSuccess: (res) => {
      setSyncFeedback(`Successfully synchronized ${res.synced_commits} commits from GitHub!`);
      queryClient.invalidateQueries({ queryKey: ["commit-analytics"] });
      setTimeout(() => setSyncFeedback(null), 4000);
    },
    onError: () => {
      setSyncFeedback("Sync failed. Ensure GitHub credentials have repository read permissions.");
      setTimeout(() => setSyncFeedback(null), 4000);
    },
  });

  const summary = analytics?.summary;
  const maxCadence = analytics?.cadence_trend?.reduce((max, p) => Math.max(max, p.commit_count), 1) || 1;
  const maxHeatmap = analytics?.heatmap?.reduce((max, p) => Math.max(max, p.commit_count), 1) || 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <GitCommit className="h-6 w-6 text-primary" />
            <span>Commit Intelligence</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Observe engineering velocity rhythm, commit cadence, and team participation patterns.
          </p>
        </div>

        {/* Global Filter Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Repository Selector */}
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="rounded-lg border border-input bg-card px-3 py-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="all">All Monitored Repositories</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          {/* Time Window Pills */}
          <div className="flex items-center rounded-lg border border-border bg-card p-0.5">
            {["7d", "14d", "30d", "90d"].map((win) => (
              <button
                key={win}
                onClick={() => setTimeWindow(win)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                  timeWindow === win
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {win}
              </button>
            ))}
          </div>

          {/* Refresh / Sync Buttons */}
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary transition-all"
            title="Refresh analytics"
          >
            <RefreshCw className={`h-3 w-3 ${isRefetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          {selectedRepoId !== "all" && (
            <button
              onClick={() => syncMutation.mutate(selectedRepoId)}
              disabled={syncMutation.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground hover:bg-secondary/80 border border-border transition-all"
            >
              {syncMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Plus className="h-3 w-3" />
              )}
              <span>Sync GitHub</span>
            </button>
          )}
        </div>
      </div>

      {/* Sync feedback alert */}
      {syncFeedback && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/10 p-3 text-xs text-primary font-medium">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{syncFeedback}</span>
        </div>
      )}

      {/* Anti-Surveillance Reassurance Banner */}
      <div className="flex items-center gap-2.5 rounded-xl border border-border/80 bg-card/60 px-4 py-2.5 text-xs text-muted-foreground shadow-sm backdrop-blur-sm">
        <ShieldCheck className="h-4 w-4 text-emerald-500 shrink-0" />
        <span>
          <strong className="text-foreground">Anti-Surveillance Commitment:</strong> Commit telemetry measures team engineering rhythm and batch size health. Developers Code Pulse never computes individual performance rankings.
        </span>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
          <p className="text-sm font-medium text-foreground">Calculating commit velocity metrics...</p>
        </div>
      ) : !summary || summary.total_commits === 0 ? (
        <EmptyState
          icon={GitCommit}
          title="No Commit Telemetry Recorded"
          description="Push commits to your monitored branches or trigger a GitHub synchronization to populate commit velocity, cadence trends, and heatmaps."
          badge="Awaiting Activity"
          actionText="Manage Repositories"
          onAction={() => window.location.assign("/repositories")}
        />
      ) : (
        <div className="space-y-6">
          {/* 4 Primary KPI Metric Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Card 1: Commit Volume */}
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">Total Commits</span>
                <GitCommit className="h-4 w-4 text-primary" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {summary.total_commits.toLocaleString()}
              </div>
              <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                <span className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  +{summary.merge_commit_count}
                </span>
                <span>merge commits excluded</span>
              </div>
            </div>

            {/* Card 2: Daily Cadence */}
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">Daily Cadence</span>
                <Calendar className="h-4 w-4 text-emerald-500" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {summary.daily_cadence} <span className="text-xs font-normal text-muted-foreground">/ day</span>
              </div>
              <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                <span>{summary.weekday_cadence} commits/weekday</span>
              </div>
            </div>

            {/* Card 3: Active Contributors */}
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">Active Contributors</span>
                <Users className="h-4 w-4 text-indigo-500" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {summary.active_contributors}
              </div>
              <div className="text-[11px] text-muted-foreground">
                Human authors in selected window
              </div>
            </div>

            {/* Card 4: Code Churn */}
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium">Code Churn</span>
                <FileCode className="h-4 w-4 text-amber-500" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {summary.total_churn.toLocaleString()}{" "}
                <span className="text-xs font-normal text-muted-foreground">lines</span>
              </div>
              <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                <span className="text-emerald-500 font-mono">+{summary.total_additions.toLocaleString()}</span>
                <span className="text-rose-500 font-mono">-{summary.total_deletions.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Commit Cadence Timeline Bar Chart */}
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Commit Cadence Timeline</h3>
                <p className="text-xs text-muted-foreground">
                  Daily commit distribution and line churn over the observation window ({analytics.start_date} to {analytics.end_date}).
                </p>
              </div>
            </div>

            {/* Custom SVG/CSS Bar Chart */}
            <div className="h-48 w-full flex items-end gap-1 pt-6 pb-2 px-2 overflow-x-auto">
              {analytics.cadence_trend.map((point) => {
                const heightPercent = Math.max(8, Math.round((point.commit_count / maxCadence) * 100));
                return (
                  <div
                    key={point.date}
                    className="flex-1 min-w-[14px] flex flex-col items-center gap-1 group relative"
                  >
                    {/* Tooltip */}
                    <div className="absolute -top-14 hidden group-hover:flex flex-col items-center z-20 pointer-events-none">
                      <div className="rounded bg-popover px-2 py-1 text-[10px] text-popover-foreground shadow-md border border-border whitespace-nowrap">
                        <div className="font-bold">{point.date}</div>
                        <div>{point.commit_count} commits</div>
                        <div className="text-[9px] text-muted-foreground">
                          +{point.additions} / -{point.deletions}
                        </div>
                      </div>
                    </div>

                    <div
                      style={{ height: `${heightPercent}%` }}
                      className={`w-full rounded-t transition-all ${
                        point.commit_count > 0
                          ? "bg-primary hover:bg-primary/80"
                          : "bg-muted/40"
                      }`}
                    />
                    <span className="text-[9px] text-muted-foreground font-mono truncate w-full text-center">
                      {point.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 7x24 Commit Activity Heatmap */}
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Commit Intensity Heatmap</h3>
                <p className="text-xs text-muted-foreground">
                  Workflow rhythm by day of week and hour of day (UTC). Identifies peak engineering activity zones.
                </p>
              </div>
            </div>

            {/* Heatmap Grid */}
            <div className="overflow-x-auto">
              <div className="min-w-[640px] space-y-1.5">
                {/* Hour labels */}
                <div className="grid grid-cols-[40px_repeat(24,1fr)] gap-1 text-[10px] font-mono text-muted-foreground text-center">
                  <div />
                  {Array.from({ length: 24 }).map((_, h) => (
                    <div key={h}>{h}</div>
                  ))}
                </div>

                {/* Day rows */}
                {DAYS_OF_WEEK.map((dayName, dIndex) => (
                  <div
                    key={dayName}
                    className="grid grid-cols-[40px_repeat(24,1fr)] gap-1 items-center"
                  >
                    <span className="text-xs font-medium text-muted-foreground">{dayName}</span>
                    {Array.from({ length: 24 }).map((_, hIndex) => {
                      const cell = analytics.heatmap.find(
                        (p) => p.day_of_week === dIndex && p.hour_of_day === hIndex
                      );
                      const count = cell ? cell.commit_count : 0;
                      const intensity = count > 0 ? Math.min(1, count / Math.max(1, maxHeatmap)) : 0;

                      return (
                        <div
                          key={hIndex}
                          title={`${dayName} at ${hIndex}:00 UTC - ${count} commits`}
                          className="h-6 rounded-sm transition-colors cursor-pointer"
                          style={{
                            backgroundColor:
                              count === 0
                                ? "var(--secondary)"
                                : `hsl(var(--primary) / ${Math.max(0.25, intensity)})`,
                          }}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Repository Comparison & Team Contributors */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Repository Breakdown */}
            <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <FolderGit2 className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Repository Breakdown</h3>
              </div>
              <div className="divide-y divide-border text-xs">
                {analytics.repository_comparison.map((repo) => (
                  <div key={repo.repository_id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-foreground">{repo.name}</div>
                      <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        <span>{repo.active_contributors_count} contributors</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-foreground">{repo.commit_count} commits</div>
                      <div className="text-[10px] text-muted-foreground font-mono">
                        +{repo.additions} / -{repo.deletions}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Contributor Participation */}
            <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-indigo-500" />
                <h3 className="text-sm font-semibold text-foreground">Team Participation</h3>
              </div>
              <div className="divide-y divide-border text-xs">
                {analytics.top_contributors.slice(0, 5).map((author) => (
                  <div key={author.author_id} className="py-2.5 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-foreground">
                        {author.login.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium text-foreground">{author.name || author.login}</div>
                        <div className="text-[10px] text-muted-foreground">@{author.login}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-foreground">{author.commit_count} commits</div>
                      <div className="text-[10px] text-muted-foreground font-mono">
                        +{author.additions} / -{author.deletions}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
