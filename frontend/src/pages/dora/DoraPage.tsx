import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock,
  Flame,
  HelpCircle,
  Layers,
  Minus,
  RefreshCw,
  Rocket,
  ShieldCheck,
} from "lucide-react";
import {
  api,
  ConnectedRepository,
  DORAOverviewResponse,
  DeploymentFrequencyDetail,
  LeadTimeDetail,
  ChangeFailureRateDetail,
  RecoveryTimeDetail,
  DeploymentListResponse,
} from "@/services/api";

export const DoraPage: React.FC = () => {
  const queryClient = useQueryClient();

  // State Filters
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [timeWindow, setTimeWindow] = useState<string>("30d");
  const [activeTab, setActiveTab] = useState<"overview" | "deployments" | "methodology">("overview");
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  const repoFilterParam = selectedRepoId !== "all" ? [selectedRepoId] : undefined;

  // 1. Fetch Repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // 2. Fetch DORA Overview
  const {
    data: dora,
    isLoading: isDoraLoading,
    refetch: refetchDora,
    isRefetching,
  } = useQuery<DORAOverviewResponse>({
    queryKey: ["dora-overview", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getDoraOverview({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
  });

  // 3. Fetch Detail Metrics
  const { data: dfDetail } = useQuery<DeploymentFrequencyDetail>({
    queryKey: ["dora-df", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getDeploymentFrequency({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
    enabled: !!dora,
  });

  const { data: ltDetail } = useQuery<LeadTimeDetail>({
    queryKey: ["dora-lt", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getLeadTime({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
    enabled: !!dora,
  });

  const { data: cfrDetail } = useQuery<ChangeFailureRateDetail>({
    queryKey: ["dora-cfr", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getChangeFailureRate({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
    enabled: !!dora,
  });

  const { data: mttrDetail } = useQuery<RecoveryTimeDetail>({
    queryKey: ["dora-mttr", selectedRepoId, timeWindow],
    queryFn: () =>
      api.analytics.getMeanTimeToRecovery({
        repository_ids: repoFilterParam,
        time_window: timeWindow,
      }),
    enabled: !!dora,
  });

  // 4. Fetch Deployments List
  const { data: deploymentList } = useQuery<DeploymentListResponse>({
    queryKey: ["deployments-list", selectedRepoId],
    queryFn: () =>
      api.deployments.list({
        repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
        environment: "production",
        page: 1,
        size: 10,
      }),
  });

  // 5. Sync Deployments Mutation
  const syncMutation = useMutation({
    mutationFn: () =>
      api.deployments.sync({
        repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
      }),
    onSuccess: (data) => {
      setSyncFeedback(data.message);
      queryClient.invalidateQueries({ queryKey: ["dora-overview"] });
      queryClient.invalidateQueries({ queryKey: ["deployments-list"] });
      setTimeout(() => setSyncFeedback(null), 4000);
    },
  });

  // Helper for performance badge colors
  const getTierBadge = (tier?: string) => {
    switch (tier ? tier.toUpperCase() : "UNKNOWN") {
      case "ELITE":
        return {
          bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
          label: "Elite",
        };
      case "HIGH":
        return {
          bg: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20",
          label: "High",
        };
      case "MEDIUM":
        return {
          bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
          label: "Medium",
        };
      case "LOW":
        return {
          bg: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
          label: "Low",
        };
      default:
        return {
          bg: "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/20",
          label: "Unknown / Insufficient Data",
        };
    }
  };

  const getTrendIcon = (direction: string) => {
    if (direction === "IMPROVED") {
      return <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500 inline mr-1" />;
    }
    if (direction === "DEGRADED") {
      return <ArrowDownRight className="w-3.5 h-3.5 text-rose-500 inline mr-1" />;
    }
    return <Minus className="w-3.5 h-3.5 text-slate-400 inline mr-1" />;
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Quick Controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              DORA Delivery Metrics
            </h1>
            {dora && (
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  getTierBadge(dora.overall_performance).bg
                }`}
              >
                Overall: {getTierBadge(dora.overall_performance).label}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Industry standard four software delivery performance pillars calculated from production deployments and verified incidents.
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

          {/* Sync Button */}
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border transition-colors disabled:opacity-50"
          >
            <Rocket className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
            Sync Deployments
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => refetchDora()}
            disabled={isRefetching}
            className="p-1.5 rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Refresh DORA Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Sync feedback notification */}
      {syncFeedback && (
        <div className="p-3 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>{syncFeedback}</span>
          </div>
        </div>
      )}

      {/* 2. Repository Filter & Data Integration Status Bar */}
      <div className="bg-card border border-border rounded-xl p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-foreground flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-primary" />
            Target Repository:
          </span>
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="bg-background border border-border rounded-lg px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Connected Repositories</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="text-muted-foreground">Source Integrations:</span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
            GitHub Actions
          </span>
          <span
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md font-medium ${
              dora?.integration_status?.github_deployments
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
            }`}
          >
            <Rocket className="w-3 h-3" />
            {dora?.integration_status?.github_deployments
              ? "Deployments Linked"
              : "Awaiting Production Deployments"}
          </span>
          <span
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md font-medium ${
              dora?.integration_status?.incident_system
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "bg-slate-500/10 text-slate-500 dark:text-slate-400"
            }`}
          >
            <Flame className="w-3 h-3" />
            {dora?.integration_status?.incident_system ? "Incidents Connected" : "No Incident Outages Logged"}
          </span>
        </div>
      </div>

      {/* 3. Four Primary DORA Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* CARD 1: Deployment Frequency */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-3 relative overflow-hidden flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Rocket className="w-4 h-4 text-primary" />
                Deployment Frequency
              </span>
              {dora?.deployment_frequency && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    getTierBadge(dora?.deployment_frequency?.performance_level).bg
                  }`}
                >
                  {getTierBadge(dora?.deployment_frequency?.performance_level).label}
                </span>
              )}
            </div>

            <div className="pt-2">
              <div className="text-2xl font-extrabold text-foreground">
                {isDoraLoading ? (
                  <div className="h-8 w-24 bg-muted/60 rounded animate-pulse" />
                ) : dora?.deployment_frequency?.status === "CALCULATED" ? (
                  <span>{dora.deployment_frequency.formatted_value}</span>
                ) : (
                  <span className="text-sm font-semibold text-slate-400 bg-slate-500/10 px-2 py-1 rounded">
                    INSUFFICIENT_DATA
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {dora?.deployment_frequency?.period || "Last 30 Days"}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5">
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Trend vs previous:</span>
              <span className="font-semibold text-foreground flex items-center">
                {getTrendIcon(dora?.deployment_frequency?.trend_direction || "NONE")}
                {dora?.deployment_frequency?.trend_percentage !== null &&
                dora?.deployment_frequency?.trend_percentage !== undefined
                  ? `${Math.abs(dora.deployment_frequency.trend_percentage)}%`
                  : "Stable"}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Sample size:</span>
              <span className="font-medium text-foreground">
                {dfDetail?.successful_deployments ?? 0} successful deploys
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Source:</span>
              <span className="text-foreground font-medium truncate max-w-[140px]">
                {dora?.deployment_frequency?.data_source}
              </span>
            </div>
          </div>

          <div className="text-[11px] bg-accent/40 p-2 rounded-lg text-muted-foreground">
            {dora?.deployment_frequency?.context_message ||
              "Counts verified successful rollouts targeting production environment."}
          </div>
        </div>

        {/* CARD 2: Lead Time for Changes */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-3 relative overflow-hidden flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-cyan-500" />
                Lead Time for Changes
              </span>
              {dora?.lead_time_for_changes && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    getTierBadge(dora?.lead_time_for_changes?.performance_level).bg
                  }`}
                >
                  {getTierBadge(dora?.lead_time_for_changes?.performance_level).label}
                </span>
              )}
            </div>

            <div className="pt-2">
              <div className="text-2xl font-extrabold text-foreground">
                {isDoraLoading ? (
                  <div className="h-8 w-24 bg-muted/60 rounded animate-pulse" />
                ) : dora?.lead_time_for_changes?.status === "CALCULATED" ? (
                  <span>{dora.lead_time_for_changes.formatted_value}</span>
                ) : (
                  <span className="text-sm font-semibold text-slate-400 bg-slate-500/10 px-2 py-1 rounded">
                    INSUFFICIENT_DATA
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Median delivery latency (Commit → Production)
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5">
            <div className="flex justify-between items-center text-muted-foreground">
              <span>P75 Latency:</span>
              <span className="font-semibold text-foreground">
                {ltDetail?.p75_hours ? `${ltDetail.p75_hours}h` : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Traceability rate:</span>
              <span className="font-medium text-foreground">
                {ltDetail ? `${Math.round(ltDetail.traceability_rate * 100)}%` : "0%"}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Sample size:</span>
              <span className="font-medium text-foreground">
                {dora?.lead_time_for_changes?.sample_size ?? 0} deployments
              </span>
            </div>
          </div>

          <div className="text-[11px] bg-accent/40 p-2 rounded-lg text-muted-foreground">
            {dora?.lead_time_for_changes?.context_message ||
              "Calculated from initial commit author timestamp to production deployment."}
          </div>
        </div>

        {/* CARD 3: Change Failure Rate */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-3 relative overflow-hidden flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <AlertOctagon className="w-4 h-4 text-amber-500" />
                Change Failure Rate
              </span>
              {dora?.change_failure_rate && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    getTierBadge(dora?.change_failure_rate?.performance_level).bg
                  }`}
                >
                  {getTierBadge(dora?.change_failure_rate?.performance_level).label}
                </span>
              )}
            </div>

            <div className="pt-2">
              <div className="text-2xl font-extrabold text-foreground">
                {isDoraLoading ? (
                  <div className="h-8 w-24 bg-muted/60 rounded animate-pulse" />
                ) : dora?.change_failure_rate?.status === "CALCULATED" ? (
                  <span>{dora.change_failure_rate.formatted_value}</span>
                ) : (
                  <span className="text-sm font-semibold text-slate-400 bg-slate-500/10 px-2 py-1 rounded">
                    INSUFFICIENT_DATA
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Ratio of failed or incident-inducing rollouts
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5">
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Degraded Rollouts:</span>
              <span className="font-semibold text-rose-500">
                {cfrDetail?.degraded_deployments ?? 0}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Linked Incidents:</span>
              <span className="font-medium text-foreground">
                {cfrDetail?.incident_linked_deployments ?? 0}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Total Prod Deploys:</span>
              <span className="font-medium text-foreground">
                {cfrDetail?.total_production_deployments ?? 0}
              </span>
            </div>
          </div>

          <div className="text-[11px] bg-accent/40 p-2 rounded-lg text-muted-foreground">
            {dora?.change_failure_rate?.context_message ||
              "Calculated from deployment execution failures and post-deploy outages."}
          </div>
        </div>

        {/* CARD 4: Time to Restore Service (MTTR) */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-3 relative overflow-hidden flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-rose-500" />
                Time to Restore Service
              </span>
              {dora?.mean_time_to_recovery && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    getTierBadge(dora?.mean_time_to_recovery?.performance_level).bg
                  }`}
                >
                  {getTierBadge(dora?.mean_time_to_recovery?.performance_level).label}
                </span>
              )}
            </div>

            <div className="pt-2">
              <div className="text-2xl font-extrabold text-foreground">
                {isDoraLoading ? (
                  <div className="h-8 w-24 bg-muted/60 rounded animate-pulse" />
                ) : dora?.mean_time_to_recovery?.status === "CALCULATED" ? (
                  <span>{dora.mean_time_to_recovery.formatted_value}</span>
                ) : (
                  <span className="text-sm font-semibold text-slate-400 bg-slate-500/10 px-2 py-1 rounded">
                    INSUFFICIENT_DATA
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Median recovery duration from incident onset
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5">
            <div className="flex justify-between items-center text-muted-foreground">
              <span>P75 Recovery:</span>
              <span className="font-semibold text-foreground">
                {mttrDetail?.p75_hours ? `${mttrDetail.p75_hours}h` : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Resolved Outages:</span>
              <span className="font-medium text-foreground">
                {mttrDetail?.resolved_incidents ?? 0}
              </span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Data completeness:</span>
              <span className="font-medium text-foreground">
                {dora?.mean_time_to_recovery?.data_completeness ? "100%" : "Requires Incident Source"}
              </span>
            </div>
          </div>

          <div className="text-[11px] bg-accent/40 p-2 rounded-lg text-muted-foreground">
            {dora?.mean_time_to_recovery?.context_message ||
              "Calculated from incident onset timestamp to verified resolution."}
          </div>
        </div>
      </div>

      {/* 4. Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-1">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "overview"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent"
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          Trends & Repository Comparison
        </button>
        <button
          onClick={() => setActiveTab("deployments")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "deployments"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent"
          }`}
        >
          <Rocket className="w-3.5 h-3.5" />
          Production Rollouts Log ({deploymentList?.total ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("methodology")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "methodology"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent"
          }`}
        >
          <HelpCircle className="w-3.5 h-3.5" />
          Calculation Methodology & Integrity
        </button>
      </div>

      {/* 5. Tab Content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Trend Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Deployment Frequency Historical Chart */}
            <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    <Rocket className="w-4 h-4 text-primary" />
                    Deployment Frequency Over Time
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Daily production rollouts over the {timeWindow} window.
                  </p>
                </div>
                <span className="text-xs font-bold text-primary">
                  {dfDetail?.successful_deployments ?? 0} Total
                </span>
              </div>

              {/* Simple Responsive SVG Bar / Timeline Chart */}
              <div className="h-44 flex items-end gap-1.5 pt-4 pb-2 border-b border-border/60">
                {dfDetail?.history && dfDetail.history.length > 0 ? (
                  dfDetail.history.map((pt, idx) => {
                    const maxVal = Math.max(...dfDetail.history.map((p) => p.value || 0), 1);
                    const heightPct = Math.max(((pt.value || 0) / maxVal) * 100, 6);
                    return (
                      <div
                        key={idx}
                        className="flex-1 flex flex-col items-center gap-1 group relative"
                      >
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full rounded-t transition-all ${
                            (pt.value || 0) > 0
                              ? "bg-primary hover:bg-primary/80"
                              : "bg-muted/40 hover:bg-muted"
                          }`}
                        />
                        <span className="text-[9px] text-muted-foreground truncate w-full text-center opacity-0 group-hover:opacity-100 transition-opacity">
                          {pt.date.slice(5)}
                        </span>
                        {/* Tooltip */}
                        <div className="absolute -top-8 bg-popover text-popover-foreground text-[10px] px-2 py-0.5 rounded shadow pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                          {pt.date}: {pt.value || 0} deploys
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
                    No production deployment timeline data available.
                  </div>
                )}
              </div>
            </div>

            {/* Lead Time for Changes Latency Chart */}
            <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-cyan-500" />
                    Lead Time for Changes Latency Trend
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Median delivery duration (hours) per recorded deployment day.
                  </p>
                </div>
                <span className="text-xs font-bold text-cyan-500">
                  {ltDetail?.median_hours ? `${ltDetail.median_hours}h Median` : "N/A"}
                </span>
              </div>

              <div className="h-44 flex items-end gap-1.5 pt-4 pb-2 border-b border-border/60">
                {ltDetail?.history && ltDetail.history.length > 0 ? (
                  ltDetail.history.map((pt, idx) => {
                    const maxVal = Math.max(...ltDetail.history.map((p) => p.value || 0), 10);
                    const heightPct = Math.max(((pt.value || 0) / maxVal) * 100, 6);
                    return (
                      <div
                        key={idx}
                        className="flex-1 flex flex-col items-center gap-1 group relative"
                      >
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full rounded-t transition-all ${
                            pt.value !== null
                              ? "bg-cyan-500 hover:bg-cyan-400"
                              : "bg-muted/40 hover:bg-muted"
                          }`}
                        />
                        <span className="text-[9px] text-muted-foreground truncate w-full text-center opacity-0 group-hover:opacity-100 transition-opacity">
                          {pt.date.slice(5)}
                        </span>
                        <div className="absolute -top-8 bg-popover text-popover-foreground text-[10px] px-2 py-0.5 rounded shadow pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                          {pt.date}: {pt.value !== null ? `${pt.value}h` : "No data"}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
                    No lead time trend data available.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Repository Breakdown Comparison Table */}
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary" />
                  Cross-Repository DORA Breakdown
                </h3>
                <p className="text-xs text-muted-foreground">
                  Multi-repo comparative performance across the four DORA pillars.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {dora?.repository_breakdowns?.length ?? 0} repositories evaluated
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground font-medium">
                  <tr>
                    <th className="py-2.5 px-4">Repository</th>
                    <th className="py-2.5 px-4">Deployment Frequency</th>
                    <th className="py-2.5 px-4">Lead Time</th>
                    <th className="py-2.5 px-4">Change Failure Rate</th>
                    <th className="py-2.5 px-4">Mean Time to Restore</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {dora?.repository_breakdowns && dora.repository_breakdowns.length > 0 ? (
                    dora.repository_breakdowns.map((repo) => (
                      <tr key={repo.repository_id} className="hover:bg-accent/30 transition-colors">
                        <td className="py-3 px-4 font-semibold text-foreground">
                          {repo.repository_name}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">
                              {repo.deployment_frequency?.formatted_value}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${
                                getTierBadge(repo.deployment_frequency?.performance_level).bg
                              }`}
                            >
                              {getTierBadge(repo.deployment_frequency?.performance_level).label}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">
                              {repo.lead_time?.formatted_value}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${
                                getTierBadge(repo.lead_time?.performance_level).bg
                              }`}
                            >
                              {getTierBadge(repo.lead_time?.performance_level).label}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">
                              {repo.change_failure_rate?.formatted_value}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${
                                getTierBadge(repo.change_failure_rate?.performance_level).bg
                              }`}
                            >
                              {getTierBadge(repo.change_failure_rate?.performance_level).label}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">
                              {repo.mean_time_to_recovery?.formatted_value}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${
                                getTierBadge(repo.mean_time_to_recovery?.performance_level).bg
                              }`}
                            >
                              {getTierBadge(repo.mean_time_to_recovery?.performance_level).label}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-xs text-muted-foreground">
                        No repository breakdown data available for this time window.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Deployments Tab */}
      {activeTab === "deployments" && (
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Rocket className="w-4 h-4 text-primary" />
                Verified Production Deployments Log
              </h3>
              <p className="text-xs text-muted-foreground">
                Traceable production rollouts with commit correlation and lead time telemetry.
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              Total {deploymentList?.total ?? 0} Deployments
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground font-medium">
                <tr>
                  <th className="py-2.5 px-4">ID</th>
                  <th className="py-2.5 px-4">Repository</th>
                  <th className="py-2.5 px-4">Environment</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Commit SHA</th>
                  <th className="py-2.5 px-4">Lead Time</th>
                  <th className="py-2.5 px-4">Deployed At</th>
                  <th className="py-2.5 px-4">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {deploymentList?.items && deploymentList.items.length > 0 ? (
                  deploymentList.items.map((d) => (
                    <tr key={d.id} className="hover:bg-accent/30 transition-colors">
                      <td className="py-2.5 px-4 font-mono text-[11px] text-muted-foreground">
                        {d.external_deployment_id || d.id.slice(0, 8)}
                      </td>
                      <td className="py-2.5 px-4 font-semibold text-foreground">
                        {d.repository_name || "Organization"}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/20">
                          {d.environment}
                        </span>
                      </td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            d.status === "SUCCESS"
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                          }`}
                        >
                          {d.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-[11px] text-foreground">
                        {d.commit_sha ? d.commit_sha.slice(0, 7) : "N/A"}
                      </td>
                      <td className="py-2.5 px-4 font-medium text-foreground">
                        {d.lead_time_seconds !== null && d.lead_time_seconds !== undefined
                          ? `${(d.lead_time_seconds / 3600).toFixed(1)}h`
                          : "Untraced"}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {new Date(d.deployed_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {d.source}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-xs text-muted-foreground">
                      No production deployments recorded yet. Use GitHub Actions with production environment tags or trigger manual sync.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Methodology Tab */}
      {activeTab === "methodology" && (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-6 text-xs text-muted-foreground">
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              DCP DORA Calculation Methodology & Ethical Data Integrity
            </h3>
            <p>
              Developers Code Pulse enforces empirical veracity. We never fabricate metrics, substitute synthetic averages, or misrepresent test runs as production releases.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-accent/40 border border-border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <Rocket className="w-4 h-4 text-primary" />
                1. Deployment Frequency
              </h4>
              <p>
                Calculated strictly from deployments targeting <code>production</code> or <code>prod</code> environments. Deploys to staging, preview environments, and routine CI builds are classified separately and omitted from production frequency.
              </p>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                <li><strong>Elite:</strong> Multiple deploys per day (&ge; 1.0/day)</li>
                <li><strong>High:</strong> Between once per day and once per week</li>
                <li><strong>Medium:</strong> Between once per week and once per month</li>
                <li><strong>Low:</strong> Fewer than once per month</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl bg-accent/40 border border-border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-cyan-500" />
                2. Lead Time for Changes
              </h4>
              <p>
                Measures the elapsed duration from when code is author-committed in a branch until that commit is deployed to production. If an individual commit cannot be resolved, the pull request merge timestamp is utilized as traceable evidence.
              </p>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                <li><strong>Elite:</strong> Less than 1 hour</li>
                <li><strong>High:</strong> 1 hour to 1 week</li>
                <li><strong>Medium:</strong> 1 week to 1 month</li>
                <li><strong>Low:</strong> More than 1 month</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl bg-accent/40 border border-border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <AlertOctagon className="w-4 h-4 text-amber-500" />
                3. Change Failure Rate
              </h4>
              <p>
                Computed as the percentage of production deployments that result in failure (deployment conclusion = FAILURE) or that cause a linked production incident within 4 hours of rollout.
              </p>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                <li><strong>Elite:</strong> 0% &ndash; 5%</li>
                <li><strong>High:</strong> 5.1% &ndash; 15%</li>
                <li><strong>Medium:</strong> 15.1% &ndash; 30%</li>
                <li><strong>Low:</strong> &gt; 30%</li>
              </ul>
            </div>

            <div className="p-4 rounded-xl bg-accent/40 border border-border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-rose-500" />
                4. Time to Restore Service (MTTR)
              </h4>
              <p>
                Calculated from verified incident onset timestamps to formal resolution timestamps. If an organization has not configured incident monitoring, DCP displays <code>INSUFFICIENT_DATA</code> rather than falsifying zero-incident recovery times.
              </p>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                <li><strong>Elite:</strong> Less than 1 hour</li>
                <li><strong>High:</strong> Less than 24 hours</li>
                <li><strong>Medium:</strong> Less than 1 week</li>
                <li><strong>Low:</strong> More than 1 week</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
