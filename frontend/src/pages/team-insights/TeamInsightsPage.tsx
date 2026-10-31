import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Clock,
  GitMerge,
  GitPullRequest,
  HeartHandshake,
  Layers,
  Lightbulb,
  RefreshCw,
  Rocket,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import {
  api,
  ConnectedRepository,
  TeamIntelligenceResponse,
  TeamTrendsResponse,
} from "@/services/api";

export const TeamInsightsPage: React.FC = () => {
  // State Filters
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [timeWindow, setTimeWindow] = useState<string>("30d");

  const repoFilterParam = selectedRepoId !== "all" ? [selectedRepoId] : undefined;

  // 1. Fetch Repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // 2. Fetch Team Intelligence
  const {
    data: team,
    isLoading: isTeamLoading,
    refetch: refetchTeam,
    isRefetching,
  } = useQuery<TeamIntelligenceResponse>({
    queryKey: ["team-intelligence", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getTeamIntelligence({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
  });

  // 3. Fetch Team Delivery Trends
  const { data: trends } = useQuery<TeamTrendsResponse>({
    queryKey: ["team-trends", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getTeamTrends({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
    enabled: !!team,
  });

  return (
    <div className="space-y-6">
      {/* 1. Header & Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Team Intelligence & Delivery Flow
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Macro-level delivery cadence, peer review dynamics, and system flow across the engineering organization.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Time Window Selector */}
          <div className="flex items-center bg-card border border-border rounded-lg p-1 text-xs">
            {["7d", "14d", "30d", "90d"].map((window) => (
              <button
                key={window}
                onClick={() => setTimeWindow(window)}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  timeWindow === window
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                {window}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refetchTeam()}
            disabled={isRefetching}
            className="p-1.5 rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Refresh Team Intelligence"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* 2. Anti-Surveillance Commitment Banner */}
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 mt-0.5 sm:mt-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
              Anti-Surveillance Privacy Charter & Ethics Guarantee
            </h4>
            <p className="text-xs text-emerald-700/90 dark:text-emerald-400/90 mt-0.5">
              {team?.anti_surveillance_notice ||
                "DCP measures macro system flow, review feedback loops, and deployment health. It strictly forbids individual developer rankings, surveillance metrics, and velocity quotas."}
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 font-bold whitespace-nowrap self-end sm:self-auto">
          ZERO INDIVIDUAL RANKINGS
        </span>
      </div>

      {/* 3. Repository Selector Bar */}
      <div className="bg-card border border-border rounded-xl p-3.5 flex items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-foreground flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-primary" />
            Repository Scope:
          </span>
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="bg-background border border-border rounded-lg px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">Organization Overview (All Repositories)</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-muted-foreground">
          Showing metrics for: <span className="font-semibold text-foreground">{team?.time_window || timeWindow}</span> window
        </div>
      </div>

      {/* 4. Macro Throughput KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Metric 1: PRs Opened */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <GitPullRequest className="w-3.5 h-3.5 text-primary" />
            PRs Opened
          </span>
          <div className="text-xl font-bold text-foreground">
            {isTeamLoading ? "..." : team?.throughput?.total_prs_opened ?? 0}
          </div>
          <span className="text-[10px] text-muted-foreground">In active window</span>
        </div>

        {/* Metric 2: PRs Merged */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <GitMerge className="w-3.5 h-3.5 text-emerald-500" />
            PRs Merged
          </span>
          <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {isTeamLoading ? "..." : team?.throughput?.total_prs_merged ?? 0}
          </div>
          <span className="text-[10px] text-muted-foreground">Completed delivery</span>
        </div>

        {/* Metric 3: Merge Rate */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-cyan-500" />
            Merge Rate
          </span>
          <div className="text-xl font-bold text-foreground">
            {isTeamLoading ? "..." : `${team?.throughput?.merge_rate_percent ?? 0}%`}
          </div>
          <span className="text-[10px] text-muted-foreground">Of finalized decisions</span>
        </div>

        {/* Metric 4: Reviews Conducted */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <HeartHandshake className="w-3.5 h-3.5 text-violet-500" />
            Peer Reviews
          </span>
          <div className="text-xl font-bold text-foreground">
            {isTeamLoading ? "..." : team?.throughput?.total_reviews ?? 0}
          </div>
          <span className="text-[10px] text-muted-foreground">Feedback actions</span>
        </div>

        {/* Metric 5: Commits */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-amber-500" />
            Code Commits
          </span>
          <div className="text-xl font-bold text-foreground">
            {isTeamLoading ? "..." : team?.throughput?.total_commits ?? 0}
          </div>
          <span className="text-[10px] text-muted-foreground">Recorded changes</span>
        </div>

        {/* Metric 6: Production Deploys */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1">
            <Rocket className="w-3.5 h-3.5 text-rose-500" />
            Production Deploys
          </span>
          <div className="text-xl font-bold text-foreground">
            {isTeamLoading ? "..." : team?.delivery_cadence?.deployments_count ?? 0}
          </div>
          <span className="text-[10px] text-muted-foreground">Verified releases</span>
        </div>
      </div>

      {/* 5. Delivery Cadence & Collaboration Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Delivery Cadence Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            Macro Delivery Speed & Latencies
          </h3>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Median Lead Time</span>
              <div className="text-lg font-bold text-foreground">
                {team?.delivery_cadence?.median_lead_time_hours !== null &&
                team?.delivery_cadence?.median_lead_time_hours !== undefined
                  ? `${team.delivery_cadence.median_lead_time_hours}h`
                  : "N/A"}
              </div>
              <p className="text-[10px] text-muted-foreground">Commit → Production</p>
            </div>

            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Review Turnaround</span>
              <div className="text-lg font-bold text-foreground">
                {team?.delivery_cadence?.median_review_turnaround_hours !== null &&
                team?.delivery_cadence?.median_review_turnaround_hours !== undefined
                  ? `${team.delivery_cadence.median_review_turnaround_hours}h`
                  : "N/A"}
              </div>
              <p className="text-[10px] text-muted-foreground">PR Open → First Review</p>
            </div>

            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Merge Latency</span>
              <div className="text-lg font-bold text-foreground">
                {team?.delivery_cadence?.median_merge_latency_hours !== null &&
                team?.delivery_cadence?.median_merge_latency_hours !== undefined
                  ? `${team.delivery_cadence.median_merge_latency_hours}h`
                  : "N/A"}
              </div>
              <p className="text-[10px] text-muted-foreground">Total PR cycle time</p>
            </div>
          </div>
        </div>

        {/* Collaboration Dynamics Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <HeartHandshake className="w-4 h-4 text-emerald-500" />
            Peer Collaboration & Code Health
          </h3>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Review Coverage</span>
              <div className="text-lg font-bold text-foreground">
                {team ? `${team?.collaboration?.review_coverage_rate ?? 0}%` : "0%"}
              </div>
              <p className="text-[10px] text-muted-foreground">Merged PRs peer-reviewed</p>
            </div>

            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Multi-Reviewer Rate</span>
              <div className="text-lg font-bold text-foreground">
                {team ? `${team?.collaboration?.multi_reviewer_pr_rate ?? 0}%` : "0%"}
              </div>
              <p className="text-[10px] text-muted-foreground">&ge; 2 reviewers on PR</p>
            </div>

            <div className="p-3 rounded-lg bg-accent/40 border border-border/60 space-y-1">
              <span className="text-[11px] text-muted-foreground">Feedback Intensity</span>
              <div className="text-lg font-bold text-foreground">
                {team ? `${team?.collaboration?.average_review_comments_per_pr ?? 0}` : "0"}
              </div>
              <p className="text-[10px] text-muted-foreground">Avg reviews/comments per PR</p>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Macro Delivery Flow Timeline Chart */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Macro Delivery Flow Timeline
            </h3>
            <p className="text-xs text-muted-foreground">
              Daily pulse of PRs opened (blue), PRs merged (green), and peer reviews (purple).
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="w-2.5 h-2.5 rounded-full bg-primary" />
              PRs Opened
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              PRs Merged
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="w-2.5 h-2.5 rounded-full bg-violet-500" />
              Reviews
            </span>
          </div>
        </div>

        <div className="h-44 flex items-end gap-1 pt-4 pb-2 border-b border-border/60">
          {trends?.series && trends.series.length > 0 ? (
            trends.series.map((pt, idx) => {
              const maxVal = Math.max(
                ...trends.series.map((p) => Math.max(p.prs_opened, p.prs_merged, p.reviews_completed)),
                4
              );
              const openPct = Math.max((pt.prs_opened / maxVal) * 100, 4);
              const mergePct = Math.max((pt.prs_merged / maxVal) * 100, 4);
              const revPct = Math.max((pt.reviews_completed / maxVal) * 100, 4);

              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1 group relative">
                  <div className="w-full flex items-end justify-center gap-0.5 h-36">
                    <div style={{ height: `${openPct}%` }} className="w-1.5 bg-primary rounded-t" />
                    <div style={{ height: `${mergePct}%` }} className="w-1.5 bg-emerald-500 rounded-t" />
                    <div style={{ height: `${revPct}%` }} className="w-1.5 bg-violet-500 rounded-t" />
                  </div>
                  <span className="text-[9px] text-muted-foreground truncate w-full text-center opacity-0 group-hover:opacity-100 transition-opacity">
                    {pt.date.slice(5)}
                  </span>
                  {/* Tooltip */}
                  <div className="absolute -top-10 bg-popover text-popover-foreground text-[10px] px-2 py-1 rounded shadow pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                    <div className="font-semibold">{pt.date}</div>
                    <div>Opened: {pt.prs_opened} | Merged: {pt.prs_merged} | Reviews: {pt.reviews_completed}</div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
              No delivery flow history available for this time window.
            </div>
          )}
        </div>
      </div>

      {/* 7. Cross-Repository Delivery Comparison Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              Cross-Repository Delivery Matrix
            </h3>
            <p className="text-xs text-muted-foreground">
              Compare throughput, merge rates, and active friction across repositories without individual scoring.
            </p>
          </div>
          <span className="text-xs text-muted-foreground">
            {team?.repository_trends?.length ?? 0} repositories
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground font-medium">
              <tr>
                <th className="py-2.5 px-4">Repository</th>
                <th className="py-2.5 px-4">PR Throughput</th>
                <th className="py-2.5 px-4">Merge Rate</th>
                <th className="py-2.5 px-4">Median Cycle Time</th>
                <th className="py-2.5 px-4">Production Deploys</th>
                <th className="py-2.5 px-4">Active Bottlenecks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {team?.repository_trends && team.repository_trends.length > 0 ? (
                team.repository_trends.map((repo) => (
                  <tr key={repo.repository_id} className="hover:bg-accent/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-foreground">
                      {repo.repository_name}
                    </td>
                    <td className="py-3 px-4 font-medium text-foreground">
                      {repo.pr_throughput} PRs
                    </td>
                    <td className="py-3 px-4 font-medium text-foreground">
                      {repo.merge_rate}%
                    </td>
                    <td className="py-3 px-4 text-foreground">
                      {repo.median_cycle_time_hours !== null && repo.median_cycle_time_hours !== undefined
                        ? `${repo.median_cycle_time_hours}h`
                        : "N/A"}
                    </td>
                    <td className="py-3 px-4 text-foreground">
                      {repo.deployment_count}
                    </td>
                    <td className="py-3 px-4">
                      {repo.active_bottlenecks > 0 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                          {repo.active_bottlenecks} Active
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                          Clear
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-xs text-muted-foreground">
                    No repositories connected or no activity recorded in this period.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 8. Systemic Team Recommendations */}
      {team?.systemic_recommendations && team.systemic_recommendations.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            Systemic Team Delivery Recommendations
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {team.systemic_recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-accent/30 border border-border/80 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-foreground">{rec.title}</h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                    {rec.category}
                  </span>
                </div>
                <p className="text-muted-foreground">{rec.observation}</p>
                <div className="pt-2 border-t border-border/40 text-foreground font-medium flex items-start gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
                  <span>{rec.suggestion}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
