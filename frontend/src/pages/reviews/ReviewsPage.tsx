import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  GitPullRequest,
  Hourglass,
  Layers,
  RefreshCw,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  api,
  ConnectedRepository,
  ReviewAnalyticsResponse,
  ReviewWorkloadResponse,
  PendingReviewQueueResponse,
} from "@/services/api";

export const ReviewsPage: React.FC = () => {
  const [timeWindow, setTimeWindow] = useState<string>("30d");
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");

  // 1. Fetch repositories for filtering
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  const repoIds = selectedRepoId !== "all" ? [selectedRepoId] : undefined;

  // 2. Fetch Review Analytics
  const {
    data: reviewAnalytics,
    isLoading: isAnalyticsLoading,
    refetch: refetchAnalytics,
    isRefetching: isAnalyticsRefetching,
  } = useQuery<ReviewAnalyticsResponse>({
    queryKey: ["review-analytics", timeWindow, selectedRepoId],
    queryFn: () =>
      api.analytics.getReviews({
        time_window: timeWindow,
        repository_ids: repoIds,
      }),
  });

  // 3. Fetch Workload Distribution & Gini Index
  const {
    data: workload,
    isLoading: isWorkloadLoading,
    refetch: refetchWorkload,
  } = useQuery<ReviewWorkloadResponse>({
    queryKey: ["review-workload", timeWindow, selectedRepoId],
    queryFn: () =>
      api.analytics.getReviewWorkload({
        time_window: timeWindow,
        repository_ids: repoIds,
      }),
  });

  // 4. Fetch Urgent Pending Queue
  const {
    data: pendingQueue,
    isLoading: isPendingLoading,
    refetch: refetchPending,
  } = useQuery<PendingReviewQueueResponse>({
    queryKey: ["pending-reviews-queue", selectedRepoId],
    queryFn: () =>
      api.analytics.getPendingReviews({
        repository_ids: repoIds,
      }),
  });

  const handleRefresh = () => {
    refetchAnalytics();
    refetchWorkload();
    refetchPending();
  };

  const metrics = reviewAnalytics?.metrics;
  const histogram = reviewAnalytics?.turnaround_histogram || [];
  const maxHistogramCount = histogram.reduce((max, h) => Math.max(max, h.count), 0) || 1;

  // Health benchmark color classes
  const getBenchmarkBadge = (status?: string) => {
    switch (status) {
      case "HEALTHY":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Healthy (&lt;8h)
          </span>
        );
      case "MODERATE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <Clock className="w-3 h-3" />
            Moderate (8-24h)
          </span>
        );
      case "CONGESTED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <AlertTriangle className="w-3 h-3" />
            Congested (&gt;24h)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">
            Optimal
          </span>
        );
    }
  };

  // Gini status badge
  const getGiniBadge = (status?: string) => {
    switch (status) {
      case "BALANCED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <Scale className="w-3 h-3" />
            Balanced Load (G ≤ 0.30)
          </span>
        );
      case "MODERATE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <Scale className="w-3 h-3" />
            Moderate Concentration (0.30 &lt; G ≤ 0.45)
          </span>
        );
      case "UNBALANCED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <AlertTriangle className="w-3 h-3" />
            Reviewer Bottleneck (G &gt; 0.45)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">
            Balanced
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Review Intelligence
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="w-3 h-3" />
              Signature Feature
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Turnaround latency percentiles, peer review coverage, and team workload dispersion.
          </p>
        </div>

        {/* Global Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Time Window Selector */}
          <div className="flex items-center bg-card border border-border rounded-lg p-1 shadow-sm">
            {(["7d", "14d", "30d", "90d"] as const).map((tw) => (
              <button
                key={tw}
                onClick={() => setTimeWindow(tw)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  timeWindow === tw
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {tw}
              </button>
            ))}
          </div>

          {/* Repository Selector */}
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="px-3 py-1.5 text-xs font-medium bg-card border border-border rounded-lg text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            <option value="all">All Repositories</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          {/* Refresh Action */}
          <button
            onClick={handleRefresh}
            disabled={isAnalyticsLoading || isAnalyticsRefetching}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-card hover:bg-muted/50 text-foreground border border-border rounded-lg shadow-sm transition-colors disabled:opacity-50"
            title="Refresh analytics data"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${
                isAnalyticsLoading || isAnalyticsRefetching ? "animate-spin text-primary" : ""
              }`}
            />
            Refresh
          </button>
        </div>
      </div>

      {/* Anti-Surveillance Manifesto Commitment Banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-gradient-to-r from-primary/5 via-card to-card border border-primary/10 shadow-sm">
        <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-semibold text-foreground">Anti-Surveillance Commitment:</span>{" "}
          Developers Code Pulse analyzes team review workflow velocity and load distribution using
          anonymized Gini dispersion coefficients. We strictly forbid individual developer speed
          targets, review quotas, or punitive telemetry.
        </div>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Time to First Review */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Time to First Review
            </span>
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">
                {metrics?.time_to_first_review?.median_hours != null
                  ? `${metrics.time_to_first_review.median_hours}h`
                  : "—"}
              </span>
              <span className="text-xs font-medium text-muted-foreground">P50 median</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between">
              {getBenchmarkBadge(metrics?.time_to_first_review?.benchmark_comparison)}
              <span className="text-xs text-muted-foreground">
                P75: {metrics?.time_to_first_review?.p75_hours ?? "—"}h | P90:{" "}
                {metrics?.time_to_first_review?.p90_hours ?? "—"}h
              </span>
            </div>
          </div>
        </div>

        {/* Metric 2: Approval Turnaround */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Approval Turnaround
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">
                {metrics?.approval_turnaround?.median_hours != null
                  ? `${metrics.approval_turnaround.median_hours}h`
                  : "—"}
              </span>
              <span className="text-xs font-medium text-muted-foreground">P50 turnaround</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>First review to sign-off</span>
              <span className="font-semibold text-foreground">
                P75: {metrics?.approval_turnaround?.p75_hours ?? "—"}h
              </span>
            </div>
          </div>
        </div>

        {/* Metric 3: Review Coverage & Rounds */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Review Coverage
            </span>
            <Layers className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">
                {metrics?.review_coverage_rate != null
                  ? `${metrics.review_coverage_rate}%`
                  : "0%"}
              </span>
              <span className="text-xs font-medium text-muted-foreground">peer reviewed</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Average rework rounds:</span>
              <span className="font-semibold text-foreground">
                {metrics?.average_review_rounds ?? 1.0}x
              </span>
            </div>
          </div>
        </div>

        {/* Metric 4: Urgent Pending Queue */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Pending Queue (≥12h)
            </span>
            <Hourglass className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span
                className={`text-3xl font-bold tracking-tight ${
                  (pendingQueue?.total_pending ?? 0) > 0 ? "text-amber-500" : "text-foreground"
                }`}
              >
                {pendingQueue?.total_pending ?? 0}
              </span>
              <span className="text-xs font-medium text-muted-foreground">PRs awaiting</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Queue threshold: ≥12h</span>
              <span
                className={`font-semibold ${
                  (pendingQueue?.total_pending ?? 0) === 0 ? "text-emerald-500" : "text-amber-500"
                }`}
              >
                {(pendingQueue?.total_pending ?? 0) === 0 ? "All caught up" : "Action needed"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Row: Turnaround Latency Histogram & Reviewer Workload Index */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Turnaround Histogram Card */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-bold text-foreground">
                  Turnaround Latency Distribution
                </h2>
              </div>
              <span className="text-xs text-muted-foreground">
                {reviewAnalytics?.start_date} to {reviewAnalytics?.end_date}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-4">
              Time elapsed from pull request opening to first substantive peer feedback.
            </p>

            {/* SVG Histogram */}
            <div className="h-44 w-full flex items-end gap-3 pt-4 pb-2 px-2">
              {histogram.map((item) => {
                const heightPercent =
                  maxHistogramCount > 0 ? (item.count / maxHistogramCount) * 100 : 0;
                return (
                  <div
                    key={item.range}
                    className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end group"
                  >
                    <span className="text-[10px] font-semibold text-muted-foreground group-hover:text-primary transition-colors">
                      {item.count}
                    </span>
                    <div className="w-full bg-muted/40 rounded-t-md overflow-hidden flex items-end h-32">
                      <div
                        style={{ height: `${Math.max(heightPercent, 4)}%` }}
                        className={`w-full transition-all duration-500 rounded-t-md ${
                          item.range === "< 2h"
                            ? "bg-emerald-500/80 group-hover:bg-emerald-500"
                            : item.range === "2h - 6h"
                            ? "bg-teal-500/80 group-hover:bg-teal-500"
                            : item.range === "6h - 24h"
                            ? "bg-primary/80 group-hover:bg-primary"
                            : item.range === "24h - 48h"
                            ? "bg-amber-500/80 group-hover:bg-amber-500"
                            : "bg-rose-500/80 group-hover:bg-rose-500"
                        }`}
                      />
                    </div>
                    <span className="text-[11px] font-medium text-muted-foreground text-center line-clamp-1">
                      {item.range}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="pt-3 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
            <span>Target: &gt;70% of reviews under 24 hours</span>
            <span className="font-semibold text-foreground">
              Total Reviewed: {histogram.reduce((acc, h) => acc + h.count, 0)} PRs
            </span>
          </div>
        </div>

        {/* Reviewer Workload Balance & Gini Concentration Index */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-bold text-foreground">
                  Reviewer Workload Balance Matrix
                </h2>
              </div>
              {getGiniBadge(workload?.workload_balance_status)}
            </div>
            <p className="text-xs text-muted-foreground mb-4">
              Mathematical Gini Coefficient (0 to 1) measuring peer review burden distribution.
            </p>

            {/* Gini Concentration Meter */}
            <div className="p-4 rounded-xl bg-muted/30 border border-border/60 mb-4">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-foreground">
                  Gini Concentration Index
                </span>
                <span className="text-sm font-bold text-foreground font-mono">
                  {(workload?.gini_coefficient ?? 0).toFixed(3)}
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2 overflow-hidden relative">
                <div
                  style={{ width: `${Math.min((workload?.gini_coefficient ?? 0) * 100, 100)}%` }}
                  className={`h-full rounded-full transition-all duration-500 ${
                    (workload?.gini_coefficient ?? 0) <= 0.3
                      ? "bg-emerald-500"
                      : (workload?.gini_coefficient ?? 0) <= 0.45
                      ? "bg-amber-500"
                      : "bg-rose-500"
                  }`}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-1.5">
                <span>0.00 (Perfect Equality)</span>
                <span>0.30</span>
                <span>0.45</span>
                <span>1.00 (Extreme Bottleneck)</span>
              </div>
            </div>

            {/* Team Review Participation List */}
            <div className="space-y-2.5 max-h-40 overflow-y-auto pr-1">
              {isWorkloadLoading ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  Calculating reviewer distribution...
                </div>
              ) : !workload?.reviewers || workload.reviewers.length === 0 ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  No peer reviews recorded in this time window.
                </div>
              ) : (
                workload.reviewers.map((rev) => (
                  <div
                    key={rev.account_id}
                    className="flex items-center justify-between text-xs p-2 rounded-lg bg-card border border-border/40 hover:border-border transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {rev.avatar_url ? (
                        <img
                          src={rev.avatar_url}
                          alt={rev.login}
                          className="w-5 h-5 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-[10px]">
                          {rev.login.slice(0, 2).toUpperCase()}
                        </div>
                      )}
                      <span className="font-semibold text-foreground">{rev.login}</span>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 text-muted-foreground text-[11px]">
                        <span>{rev.reviews_conducted} reviews</span>
                        <span>•</span>
                        <span className="text-emerald-500 font-medium">
                          {rev.approvals_given} approvals
                        </span>
                      </div>
                      <span className="font-mono text-xs font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded">
                        {rev.review_share_percentage}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="pt-3 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
            <span>Total Reviews: {workload?.total_reviews ?? 0}</span>
            <span>Active Reviewers: {workload?.reviewers?.length ?? 0}</span>
          </div>
        </div>
      </div>

      {/* Urgent Pending Review Queue Table */}
      <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div className="flex items-center gap-2">
            <Hourglass className="w-4 h-4 text-amber-500" />
            <h2 className="text-base font-bold text-foreground">
              Urgent Pending Review Queue
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
              {pendingQueue?.total_pending ?? 0} PRs waiting
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Pull requests open for ≥12 hours awaiting first substantive peer review.
          </p>
        </div>

        {isPendingLoading ? (
          <div className="py-12 text-center text-xs text-muted-foreground">
            Loading urgent pending review queue...
          </div>
        ) : !pendingQueue?.items || pendingQueue.items.length === 0 ? (
          <div className="py-12 text-center flex flex-col items-center justify-center gap-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/70" />
            <p className="text-sm font-semibold text-foreground">
              All Pull Requests Promptly Reviewed!
            </p>
            <p className="text-xs text-muted-foreground max-w-md">
              There are currently no active pull requests waiting longer than 12 hours for peer
              review. Flow velocity is optimal.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 border-b border-border text-muted-foreground font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Pull Request</th>
                  <th className="py-2.5 px-3">Repository</th>
                  <th className="py-2.5 px-3">Author</th>
                  <th className="py-2.5 px-3">Waiting Duration</th>
                  <th className="py-2.5 px-3">Requested Reviewers</th>
                  <th className="py-2.5 px-3">Opened</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {pendingQueue.items.map((item) => (
                  <tr key={item.pull_request_id} className="hover:bg-muted/30 transition-colors">
                    {/* Pull Request Title and Number */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <GitPullRequest className="w-4 h-4 text-primary shrink-0" />
                        <div>
                          <span className="font-semibold text-foreground line-clamp-1">
                            {item.title}
                          </span>
                          <span className="font-mono text-muted-foreground text-[11px]">
                            #{item.number}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Repository Name */}
                    <td className="py-3 px-3 font-medium text-foreground">
                      {item.repository_name}
                    </td>

                    {/* Author */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5">
                        {item.author_avatar ? (
                          <img
                            src={item.author_avatar}
                            alt={item.author_login || "author"}
                            className="w-4 h-4 rounded-full object-cover"
                          />
                        ) : (
                          <div className="w-4 h-4 rounded-full bg-muted text-[9px] flex items-center justify-center font-bold">
                            {(item.author_login || "U").slice(0, 1)}
                          </div>
                        )}
                        <span className="text-foreground">{item.author_login || "unknown"}</span>
                      </div>
                    </td>

                    {/* Waiting Duration Badge */}
                    <td className="py-3 px-3">
                      {item.waiting_hours >= 24 ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold text-[11px] bg-rose-500/10 text-rose-500 border border-rose-500/20">
                          <AlertTriangle className="w-3 h-3" />
                          {item.waiting_hours}h wait
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold text-[11px] bg-amber-500/10 text-amber-500 border border-amber-500/20">
                          <Clock className="w-3 h-3" />
                          {item.waiting_hours}h wait
                        </span>
                      )}
                    </td>

                    {/* Requested Reviewers */}
                    <td className="py-3 px-3">
                      <div className="flex flex-wrap items-center gap-1">
                        {item.requested_reviewers.length === 0 ? (
                          <span className="text-muted-foreground italic text-[11px]">
                            None requested
                          </span>
                        ) : (
                          item.requested_reviewers.map((rev) => (
                            <span
                              key={rev}
                              className="px-1.5 py-0.5 rounded bg-muted text-foreground text-[11px] font-mono"
                            >
                              @{rev}
                            </span>
                          ))
                        )}
                      </div>
                    </td>

                    {/* Opened Timestamp */}
                    <td className="py-3 px-3 text-muted-foreground font-mono text-[11px]">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
