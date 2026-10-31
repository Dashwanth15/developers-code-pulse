import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  RefreshCw,
  Cpu,
  ShieldAlert,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Clock,
} from "lucide-react";
import {
  api,
  AIInsightResponse,
  AIInsightListResponse,
  AIInsightGenerateRequest,
  ConnectedRepository,
} from "@/services/api";
import { EmptyState } from "@/components/common/EmptyState";
import { cn } from "@/utils/cn";

export const AiInsightsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<string>("30d");
  const [expandedInsightIds, setExpandedInsightIds] = useState<Record<string, boolean>>({});

  // 1. Fetch Repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // 2. Fetch AI Insights
  const {
    data: insightsData,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery<AIInsightListResponse>({
    queryKey: ["ai-insights", selectedType, selectedRepoId],
    queryFn: () =>
      api.insights.list({
        insight_type: selectedType !== "all" ? selectedType : undefined,
        repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
        limit: 50,
      }),
  });

  // 3. Generate Mutation
  const generateMutation = useMutation({
    mutationFn: (payload: AIInsightGenerateRequest) => api.insights.generate(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-insights"] });
    },
  });

  const handleRunAnalysis = () => {
    generateMutation.mutate({
      repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
      time_range: timeRange,
    });
  };

  const toggleExpand = (id: string) => {
    setExpandedInsightIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const getInsightTypeBadge = (type: string) => {
    switch (type) {
      case "POSITIVE_TREND":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            <TrendingUp className="h-3 w-3" /> Positive Trend
          </span>
        );
      case "DETERIORATING_TREND":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-600 dark:text-rose-400">
            <TrendingDown className="h-3 w-3" /> Degrading Trend
          </span>
        );
      case "WORKFLOW_BOTTLENECK":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
            <AlertTriangle className="h-3 w-3" /> Workflow Friction
          </span>
        );
      case "DORA_EVALUATION":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-semibold text-purple-600 dark:text-purple-400">
            <Cpu className="h-3 w-3" /> DORA Evaluation
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-600 dark:text-blue-400">
            <Sparkles className="h-3 w-3" /> Recommendation
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              AI Engineering Insights
            </h1>
            <span className="rounded-md bg-purple-500/10 px-2 py-0.5 text-xs font-semibold uppercase text-purple-600 dark:text-purple-400">
              Grounded Telemetry
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Evidence-backed explanations, period-over-period trend analysis, and actionable systemic recommendations synthesized from verified metrics.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="h-9 rounded-lg border border-border bg-card px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="7d">Last 7 Days</option>
            <option value="14d">Last 14 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>

          <button
            onClick={handleRunAnalysis}
            disabled={generateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {generateMutation.isPending ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Synthesizing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run AI Synthesis
              </>
            )}
          </button>
        </div>
      </div>

      {/* Provider Status & Anti-Surveillance Banner */}
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-foreground">
              <span>AI Provider:</span>
              <span className="rounded bg-secondary px-2 py-0.5 text-[11px] font-semibold text-foreground uppercase">
                {insightsData?.provider_name === "gemini" ? "Google Gemini 2.5 Flash" : "Deterministic Engine"}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-3 w-3" /> Verified Grounded
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Strictly grounded in repository telemetry. 0 invented metrics. 0 individual velocity tracking. Traceable evidence provenance.
            </p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isRefetching && "animate-spin")} />
          Refresh Feed
        </button>
      </div>

      {/* Executive Summary Card */}
      {insightsData?.executive_summary && (
        <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 shadow-sm">
          <div className="flex items-center gap-2 border-b border-primary/10 pb-3">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-bold text-foreground uppercase tracking-wider">
              Engineering Executive Synthesis
            </h2>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-foreground/90 whitespace-pre-line font-normal">
            {insightsData.executive_summary}
          </p>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mr-1">
            <SlidersHorizontal className="h-3.5 w-3.5" /> Filter Feed:
          </span>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Insight Categories</option>
            <option value="POSITIVE_TREND">Positive Trends</option>
            <option value="DETERIORATING_TREND">Degrading Trends</option>
            <option value="WORKFLOW_BOTTLENECK">Workflow Bottlenecks</option>
            <option value="DORA_EVALUATION">DORA Evaluations</option>
            <option value="SYSTEMIC_RECOMMENDATION">Recommendations</option>
          </select>

          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Repositories</option>
            {repositories?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        <span className="text-xs text-muted-foreground">
          Showing {insightsData?.items?.length ?? 0} insights
        </span>
      </div>

      {/* Insights Stream */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-card">
          <div className="flex flex-col items-center gap-2">
            <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            <p className="text-xs text-muted-foreground">
              Retrieving AI insights feed...
            </p>
          </div>
        </div>
      ) : insightsData?.items && insightsData.items.length > 0 ? (
        <div className="space-y-4">
          {insightsData.items.map((insight: AIInsightResponse) => {
            const isExpanded = !!expandedInsightIds[insight.id];
            const repoName =
              repositories?.find((r) => r.id === insight.repository_id)?.name ||
              "Organization Wide";

            return (
              <div
                key={insight.id}
                className="overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-all hover:border-border/80"
              >
                {/* Card Header */}
                <div className="p-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-wrap items-center gap-2">
                      {getInsightTypeBadge(insight.insight_type)}
                      <span className="rounded bg-secondary px-2 py-0.5 text-[10px] font-medium text-foreground">
                        {repoName}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="rounded-full bg-secondary px-2 py-0.5 font-semibold text-foreground">
                        {Math.round(insight.confidence * 100)}% Confidence
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(insight.generated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {/* Title & Explanation */}
                  <h3 className="mt-3 text-base font-bold text-foreground">
                    {insight.title}
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    {insight.explanation}
                  </p>

                  {/* Recommendation Callout */}
                  {insight.recommendation && (
                    <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3.5 text-xs text-emerald-950 dark:text-emerald-200">
                      <Lightbulb className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
                      <div>
                        <span className="font-semibold uppercase tracking-wider text-[10px] block text-emerald-700 dark:text-emerald-300">
                          Recommended Action:
                        </span>
                        <p className="mt-0.5 font-medium leading-relaxed">
                          {insight.recommendation}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Toggle Evidence Dropdown */}
                  {insight.evidence && Object.keys(insight.evidence).length > 0 && (
                    <div className="mt-4 border-t border-border pt-3">
                      <button
                        onClick={() => toggleExpand(insight.id)}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-3.5 w-3.5" /> Hide Provenance & Evidence ({Object.keys(insight.evidence).length} metrics)
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3.5 w-3.5" /> View Supporting Telemetry Evidence ({Object.keys(insight.evidence).length} metrics)
                          </>
                        )}
                      </button>

                      {isExpanded && (
                        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 rounded-lg border border-border/80 bg-secondary/30 p-3">
                          {Object.entries(insight.evidence).map(([k, v]) => (
                            <div
                              key={k}
                              className="rounded border border-border/50 bg-card p-2 text-xs"
                            >
                              <div className="text-[10px] uppercase tracking-wider text-muted-foreground truncate">
                                {k.replace(/_/g, " ")}
                              </div>
                              <div className="mt-0.5 font-bold text-foreground truncate">
                                {typeof v === "object" ? JSON.stringify(v) : String(v)}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                <div className="flex items-center justify-between border-t border-border bg-secondary/20 px-5 py-2.5 text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span>Synthesized by</span>
                    <span className="font-semibold text-foreground uppercase">
                      {insight.provider} ({insight.model})
                    </span>
                  </div>
                  <span className="italic">
                    ID: {insight.id.slice(0, 8)}...
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={Sparkles}
          title="No AI Insights Generated Yet"
          description="Trigger an AI synthesis run to analyze delivery cadence, detect workflow friction, and generate evidence-backed recommendations."
          actionText="Run Initial Analysis"
          onAction={handleRunAnalysis}
          badge="AI Insights Engine"
        />
      )}

      {/* Anti-Surveillance Ethical Notice */}
      <div className="rounded-lg border border-border/80 bg-secondary/20 p-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <ShieldAlert className="h-4 w-4 text-primary" />
          <span>Anti-Surveillance & Grounding Manifesto Compliance</span>
        </div>
        <p className="mt-1 leading-relaxed">
          Developers Code Pulse evaluates pipeline dynamics, review queues, and deployment cadence. Insights strictly focus on systemic team workflow improvements. The system never generates individual developer velocity scores, rankings, or performance evaluations.
        </p>
      </div>
    </div>
  );
};

export default AiInsightsPage;
