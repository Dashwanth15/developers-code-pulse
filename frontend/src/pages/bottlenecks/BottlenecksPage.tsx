import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Scale,
  RefreshCw,
  ShieldCheck,
  Zap,
  GitPullRequest,
  GitMerge,
  Layers,
  ChevronRight,
  Filter,
  X,
  Sparkles,
  Info,
} from "lucide-react";
import {
  api,
  ConnectedRepository,
  BottleneckResponse,
  BottleneckListResponse,
  BottleneckSummaryResponse,
  BottleneckRecommendationsResponse,
} from "@/services/api";

export const BottlenecksPage: React.FC = () => {
  const queryClient = useQueryClient();

  // State Filters
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("ACTIVE");
  const [selectedBottleneck, setSelectedBottleneck] = useState<BottleneckResponse | null>(null);
  const [detectionFeedback, setDetectionFeedback] = useState<string | null>(null);

  // 1. Fetch repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  const repoFilterParam = selectedRepoId !== "all" ? selectedRepoId : undefined;

  // 2. Fetch Bottleneck Summary
  const {
    data: summary,
    isLoading: isSummaryLoading,
    refetch: refetchSummary,
  } = useQuery<BottleneckSummaryResponse>({
    queryKey: ["bottlenecks-summary", repoFilterParam],
    queryFn: () => api.bottlenecks.getSummary({ repository_id: repoFilterParam }),
  });

  // 3. Fetch Bottlenecks List
  const {
    data: bottleneckList,
    isLoading: isListLoading,
    refetch: refetchList,
    isRefetching: isListRefetching,
  } = useQuery<BottleneckListResponse>({
    queryKey: ["bottlenecks-list", repoFilterParam, severityFilter, typeFilter, statusFilter],
    queryFn: () =>
      api.bottlenecks.list({
        repository_id: repoFilterParam,
        severity: severityFilter !== "all" ? severityFilter : undefined,
        bottleneck_type: typeFilter !== "all" ? typeFilter : undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        page: 1,
        size: 50,
      }),
  });

  // 4. Fetch Actionable Recommendations
  const {
    data: recommendationsData,
    refetch: refetchRecs,
  } = useQuery<BottleneckRecommendationsResponse>({
    queryKey: ["bottlenecks-recommendations", repoFilterParam],
    queryFn: () => api.bottlenecks.getRecommendations({ repository_id: repoFilterParam }),
  });

  // 5. Trigger Detection Mutation
  const detectMutation = useMutation({
    mutationFn: () =>
      api.bottlenecks.detect({
        repository_id: repoFilterParam,
        time_window: "30d",
      }),
    onSuccess: (data) => {
      setDetectionFeedback(
        data.message || `Detection complete! ${data.total_bottlenecks} bottlenecks evaluated.`
      );
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-summary"] });
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-list"] });
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-recommendations"] });
      setTimeout(() => setDetectionFeedback(null), 6000);
    },
    onError: (err: Error) => {
      setDetectionFeedback(`Detection failed: ${err.message}`);
      setTimeout(() => setDetectionFeedback(null), 6000);
    },
  });

  // 6. Status Update Mutation
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.bottlenecks.updateStatus(id, status),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-summary"] });
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-list"] });
      queryClient.invalidateQueries({ queryKey: ["bottlenecks-recommendations"] });
      if (selectedBottleneck?.id === updated.id) {
        setSelectedBottleneck(updated);
      }
    },
  });

  const handleRefresh = () => {
    refetchSummary();
    refetchList();
    refetchRecs();
  };

  // Severity color helpers
  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <AlertTriangle className="w-3 h-3" />
            Critical
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20">
            <AlertTriangle className="w-3 h-3" />
            High
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <Clock className="w-3 h-3" />
            Medium
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
            <Info className="w-3 h-3" />
            Low
          </span>
        );
    }
  };

  // Confidence color helpers
  const getConfidenceBadge = (conf: string) => {
    switch (conf) {
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-500">
            Verified Baseline
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-teal-500/10 text-teal-500">
            Moderate Sample
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-violet-500/10 text-violet-500">
            Threshold Alert
          </span>
        );
    }
  };

  // Category Icon & Label
  const getCategoryMeta = (type: string) => {
    switch (type) {
      case "PR_REVIEW_DELAY":
        return { label: "PR Review Delay", icon: Clock, color: "text-amber-500" };
      case "APPROVAL_DELAY":
        return { label: "Approval Friction", icon: CheckCircle2, color: "text-emerald-500" };
      case "MERGE_DELAY":
        return { label: "Merge Latency", icon: GitMerge, color: "text-indigo-500" };
      case "REVIEWER_CONCENTRATION":
        return { label: "Reviewer Capacity", icon: Scale, color: "text-purple-500" };
      case "PR_SIZE_OVERSIZED":
        return { label: "PR Size Divergence", icon: Layers, color: "text-blue-500" };
      case "REPOSITORY_BACKLOG":
        return { label: "Repository Backlog", icon: GitPullRequest, color: "text-rose-500" };
      default:
        return { label: type, icon: AlertTriangle, color: "text-muted-foreground" };
    }
  };

  const totalActive = summary?.total_active ?? 0;
  const criticalHighCount = (summary?.critical_count ?? 0) + (summary?.high_count ?? 0);
  const affectedRepos = summary?.affected_repositories_count ?? 0;
  const resolvedCount = summary?.resolved_count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Bottleneck Detection Engine
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <Sparkles className="w-3 h-3" />
              Intelligence Engine
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Deterministic identification of workflow delivery friction, review lag, and reviewer capacity congestion.
          </p>
        </div>

        {/* Global Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
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

          {/* Trigger Detection Run */}
          <button
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${detectMutation.isPending ? "animate-spin" : ""}`} />
            {detectMutation.isPending ? "Evaluating..." : "Run Detection"}
          </button>

          {/* Refresh Action */}
          <button
            onClick={handleRefresh}
            disabled={isListLoading || isListRefetching}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-card hover:bg-muted/50 text-foreground border border-border rounded-lg shadow-sm transition-colors disabled:opacity-50"
            title="Refresh bottlenecks"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${
                isListLoading || isListRefetching ? "animate-spin text-primary" : ""
              }`}
            />
            Refresh
          </button>
        </div>
      </div>

      {/* Detection Feedback Banner */}
      {detectionFeedback && (
        <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-primary/20 text-xs text-foreground shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>{detectionFeedback}</span>
          </div>
          <button
            onClick={() => setDetectionFeedback(null)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Anti-Surveillance Manifesto Commitment Banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-gradient-to-r from-amber-500/5 via-card to-card border border-amber-500/10 shadow-sm">
        <ShieldCheck className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-semibold text-foreground">Anti-Surveillance Commitment:</span>{" "}
          Developers Code Pulse analyzes systemic workflow queues, review lag, and reviewer capacity
          distribution. We strictly forbid employee performance scores, individual developer rankings,
          or personal velocity quotas.
        </div>
      </div>

      {/* Overview KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Total Active Bottlenecks */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Active Bottlenecks
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : totalActive}
              </span>
              <span className="text-xs font-medium text-muted-foreground">workflow issues</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Delivery friction detected</span>
              <span className="font-semibold text-foreground">
                {summary?.medium_count ?? 0} Moderate
              </span>
            </div>
          </div>
        </div>

        {/* Metric 2: Critical & High Severity */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Critical & High
            </span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span
                className={`text-3xl font-bold tracking-tight ${
                  criticalHighCount > 0 ? "text-rose-500" : "text-foreground"
                }`}
              >
                {isSummaryLoading ? "—" : criticalHighCount}
              </span>
              <span className="text-xs font-medium text-muted-foreground">urgent blockages</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Critical: {summary?.critical_count ?? 0}</span>
              <span className="font-semibold text-foreground">
                High: {summary?.high_count ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Metric 3: Affected Repositories */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Affected Repositories
            </span>
            <GitPullRequest className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : affectedRepos}
              </span>
              <span className="text-xs font-medium text-muted-foreground">with active friction</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Monitored codebases</span>
              <span className="font-semibold text-foreground">
                Total: {repositories?.length ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Metric 4: Resolved Bottlenecks */}
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Resolved Bottlenecks
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-emerald-500">
                {isSummaryLoading ? "—" : resolvedCount}
              </span>
              <span className="text-xs font-medium text-muted-foreground">issues remediated</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Efficiency restored</span>
              <span className="font-semibold text-emerald-500">Healthy Flow</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl bg-card border border-border shadow-sm flex flex-wrap items-center justify-between gap-4">
        {/* Severity Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1 mr-1">
            <Filter className="w-3.5 h-3.5" /> Severity:
          </span>
          {(["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors capitalize ${
                severityFilter === sev
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}
            >
              {sev.toLowerCase()}
            </button>
          ))}
        </div>

        {/* Category Selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-muted-foreground mr-1">Category:</span>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2.5 py-1 text-xs font-medium bg-card border border-border rounded-lg text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer"
          >
            <option value="all">All Categories</option>
            <option value="PR_REVIEW_DELAY">PR Review Delay</option>
            <option value="APPROVAL_DELAY">Approval Friction</option>
            <option value="MERGE_DELAY">Merge Latency</option>
            <option value="REVIEWER_CONCENTRATION">Reviewer Capacity</option>
            <option value="PR_SIZE_OVERSIZED">PR Size Divergence</option>
            <option value="REPOSITORY_BACKLOG">Repository Backlog</option>
          </select>
        </div>

        {/* Status Tabs */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-muted-foreground mr-1">Status:</span>
          {(["ACTIVE", "ACKNOWLEDGED", "RESOLVED", "all"] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors capitalize ${
                statusFilter === st
                  ? "bg-muted text-foreground font-semibold border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {st.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Grid: Bottlenecks Feed & Prioritized Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Bottleneck Feed Table */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              Detected Bottlenecks ({bottleneckList?.total ?? 0})
            </h2>
            <span className="text-xs text-muted-foreground">
              Showing active delivery friction items
            </span>
          </div>

          {isListLoading ? (
            <div className="p-12 text-center text-xs text-muted-foreground rounded-xl bg-card border border-border">
              Evaluating delivery metrics and running bottleneck algorithms...
            </div>
          ) : !bottleneckList?.items || bottleneckList.items.length === 0 ? (
            <div className="p-12 text-center rounded-xl bg-card border border-border flex flex-col items-center justify-center gap-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500/70" />
              <p className="text-sm font-semibold text-foreground">Zero Bottlenecks Detected!</p>
              <p className="text-xs text-muted-foreground max-w-sm">
                No active delivery friction or review congestion matches your current filter criteria.
                Engineering flow velocity is optimal.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {bottleneckList.items.map((item) => {
                const meta = getCategoryMeta(item.bottleneck_type);
                const IconComponent = meta.icon;
                return (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl bg-card border border-border/80 hover:border-primary/40 transition-all shadow-sm flex flex-col justify-between gap-3 group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg bg-muted/50 ${meta.color} shrink-0 mt-0.5`}>
                          <IconComponent className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            {getSeverityBadge(item.severity)}
                            {getConfidenceBadge(item.confidence)}
                            <span className="text-xs text-muted-foreground font-medium">
                              {item.repository_name || "Organization-wide"}
                            </span>
                          </div>
                          <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                            {item.title}
                          </h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                            {item.description}
                          </p>
                        </div>
                      </div>

                      {/* Status & Actions */}
                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <span
                          className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                            item.status === "ACTIVE"
                              ? "bg-amber-500/10 text-amber-500"
                              : item.status === "ACKNOWLEDGED"
                              ? "bg-blue-500/10 text-blue-500"
                              : "bg-emerald-500/10 text-emerald-500"
                          }`}
                        >
                          {item.status}
                        </span>
                        <button
                          onClick={() => setSelectedBottleneck(item)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline mt-1"
                        >
                          View Evidence <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Bottom Evidence Preview Strip */}
                    <div className="pt-3 border-t border-border/40 flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-3">
                        <span>
                          Observed:{" "}
                          <span className="font-semibold text-foreground font-mono">
                            {typeof item.evidence?.observed_value === "number"
                              ? (item.evidence.observed_value as number).toFixed(1)
                              : String(item.evidence?.observed_value ?? "—")}
                          </span>
                        </span>
                        <span>•</span>
                        <span>
                          First seen: {new Date(item.first_observed_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {item.status === "ACTIVE" && (
                          <button
                            onClick={() =>
                              statusMutation.mutate({ id: item.id, status: "ACKNOWLEDGED" })
                            }
                            className="text-xs px-2 py-0.5 rounded bg-muted hover:bg-muted/80 text-foreground transition-colors"
                          >
                            Acknowledge
                          </button>
                        )}
                        {item.status !== "RESOLVED" && (
                          <button
                            onClick={() =>
                              statusMutation.mutate({ id: item.id, status: "RESOLVED" })
                            }
                            className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 font-medium transition-colors"
                          >
                            Mark Resolved
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Col: Prioritized Recommendations & Distribution */}
        <div className="space-y-6">
          {/* Actionable Recommendations Panel */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-bold text-foreground">
                    Actionable Flow Guidance
                  </h3>
                </div>
                <span className="text-xs text-muted-foreground">
                  {recommendationsData?.total_recommendations ?? 0} active
                </span>
              </div>
              <p className="text-xs text-muted-foreground mb-4">
                Prioritized engineering process advice grounded in empirical evidence.
              </p>

              <div className="space-y-3">
                {!recommendationsData?.recommendations ||
                recommendationsData.recommendations.length === 0 ? (
                  <div className="py-8 text-center text-xs text-muted-foreground">
                    No active workflow recommendations at this time.
                  </div>
                ) : (
                  recommendationsData.recommendations.slice(0, 5).map((rec) => (
                    <div
                      key={rec.bottleneck_type}
                      className="p-3 rounded-lg bg-muted/30 border border-border/60 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground line-clamp-1">
                          {rec.title}
                        </span>
                        {getSeverityBadge(rec.severity)}
                      </div>
                      <p className="text-muted-foreground leading-relaxed">{rec.recommendation}</p>
                      <div className="pt-1 text-[11px] text-muted-foreground flex items-center justify-between">
                        <span>Impact: {rec.impact}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Severity & Category Distribution Panel */}
          <div className="p-5 rounded-xl bg-card border border-border shadow-sm">
            <h3 className="text-sm font-bold text-foreground mb-1">Bottlenecks by Severity</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Breakdown of current operational friction.
            </p>

            <div className="space-y-2.5 text-xs">
              {[
                { label: "Critical", count: summary?.critical_count ?? 0, color: "bg-rose-500" },
                { label: "High", count: summary?.high_count ?? 0, color: "bg-orange-500" },
                { label: "Medium", count: summary?.medium_count ?? 0, color: "bg-amber-500" },
                { label: "Low", count: summary?.low_count ?? 0, color: "bg-blue-500" },
              ].map((item) => {
                const total = summary?.total_active || 1;
                const pct = Math.round((item.count / total) * 100);
                return (
                  <div key={item.label} className="space-y-1">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>{item.label}</span>
                      <span className="font-semibold text-foreground">{item.count}</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                      <div
                        style={{ width: `${pct}%` }}
                        className={`h-full rounded-full ${item.color} transition-all duration-500`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Bottleneck Evidence Modal */}
      {selectedBottleneck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-2xl rounded-2xl bg-card border border-border shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-border flex items-start justify-between gap-4 bg-muted/20">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  {getSeverityBadge(selectedBottleneck.severity)}
                  {getConfidenceBadge(selectedBottleneck.confidence)}
                  <span className="text-xs font-semibold text-muted-foreground">
                    {selectedBottleneck.repository_name || "Organization-wide"}
                  </span>
                </div>
                <h2 className="text-base font-bold text-foreground">
                  {selectedBottleneck.title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedBottleneck(null)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs">
              {/* Description */}
              <div>
                <h4 className="font-semibold text-foreground uppercase tracking-wider text-[11px] mb-1.5">
                  Friction Summary
                </h4>
                <p className="text-muted-foreground leading-relaxed bg-muted/30 p-3 rounded-lg border border-border/50">
                  {selectedBottleneck.description}
                </p>
              </div>

              {/* Actionable Recommendation */}
              <div>
                <h4 className="font-semibold text-foreground uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-primary" /> Recommended Engineering Action
                </h4>
                <div className="p-3.5 rounded-lg bg-primary/5 border border-primary/20 text-foreground leading-relaxed">
                  {selectedBottleneck.recommendation}
                </div>
              </div>

              {/* Empirical Evidence Details */}
              <div>
                <h4 className="font-semibold text-foreground uppercase tracking-wider text-[11px] mb-1.5">
                  Empirical Evidence & Telemetry
                </h4>
                <div className="p-3 rounded-lg bg-card border border-border font-mono text-[11px] space-y-1 overflow-x-auto text-muted-foreground">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(selectedBottleneck.evidence, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Timeline & Metadata */}
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/60 text-muted-foreground text-[11px]">
                <div>
                  <span className="font-semibold text-foreground">First Observed:</span>{" "}
                  {new Date(selectedBottleneck.first_observed_at).toLocaleString()}
                </div>
                <div>
                  <span className="font-semibold text-foreground">Last Evaluated:</span>{" "}
                  {new Date(selectedBottleneck.last_observed_at).toLocaleString()}
                </div>
                <div>
                  <span className="font-semibold text-foreground">Unique Fingerprint:</span>{" "}
                  <span className="font-mono">{selectedBottleneck.fingerprint.slice(0, 12)}...</span>
                </div>
                <div>
                  <span className="font-semibold text-foreground">Current Status:</span>{" "}
                  <span className="font-bold text-foreground">{selectedBottleneck.status}</span>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Change Status:</span>
                {(["ACTIVE", "ACKNOWLEDGED", "RESOLVED", "IGNORED"] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() =>
                      statusMutation.mutate({ id: selectedBottleneck.id, status: st })
                    }
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      selectedBottleneck.status === st
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setSelectedBottleneck(null)}
                className="px-3 py-1.5 text-xs font-semibold bg-muted hover:bg-muted/80 text-foreground rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
