import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Download,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Sparkles,
  Trash2,
  Eye,
  SlidersHorizontal,
  Mail,
  X,
  FileCheck,
} from "lucide-react";
import {
  api,
  ReportResponse,
  ReportListResponse,
  ReportGenerateRequest,
  ScheduledReportListResponse,
  ScheduledReportCreateRequest,
  ConnectedRepository,
} from "@/services/api";
import { EmptyState } from "@/components/common/EmptyState";
import { cn } from "@/utils/cn";

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Active Tab: generated vs scheduled
  const [activeTab, setActiveTab] = useState<"reports" | "schedules">("reports");

  // Filters
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedRepoId, setSelectedRepoId] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  // Modals
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [viewingReport, setViewingReport] = useState<ReportResponse | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Generate Form State
  const [genType, setGenType] = useState<ReportGenerateRequest["report_type"]>("ENGINEERING_HEALTH");
  const [genRepoId, setGenRepoId] = useState<string>("");
  const [genTimeRange, setGenTimeRange] = useState<ReportGenerateRequest["time_range"]>("30d");
  const [genCustomStart, setGenCustomStart] = useState<string>("");
  const [genCustomEnd, setGenCustomEnd] = useState<string>("");
  const [genTitle, setGenTitle] = useState<string>("");
  const [genIncludeAI, setGenIncludeAI] = useState<boolean>(true);

  // Schedule Form State
  const [schedType, setSchedType] = useState<ScheduledReportCreateRequest["report_type"]>("WEEKLY");
  const [schedRepoId, setSchedRepoId] = useState<string>("");
  const [schedFreq, setSchedFreq] = useState<ScheduledReportCreateRequest["frequency"]>("WEEKLY");
  const [schedTimezone, setSchedTimezone] = useState<string>("UTC");
  const [schedRecipients, setSchedRecipients] = useState<string>("");

  // 1. Fetch Repositories
  const { data: repositories } = useQuery<ConnectedRepository[]>({
    queryKey: ["connected-repositories"],
    queryFn: () => api.repositories.list(),
  });

  // 2. Fetch Reports List
  const {
    data: reportsData,
    isLoading: isReportsLoading,
    refetch: refetchReports,
    isRefetching: isReportsRefetching,
  } = useQuery<ReportListResponse>({
    queryKey: ["reports-list", selectedType, selectedRepoId, selectedStatus],
    queryFn: () =>
      api.reports.list({
        report_type: selectedType !== "all" ? selectedType : undefined,
        repository_id: selectedRepoId !== "all" ? selectedRepoId : undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        page: 1,
        size: 50,
      }),
  });

  // 3. Fetch Scheduled Reports
  const {
    data: schedulesData,
    isLoading: isSchedulesLoading,
  } = useQuery<ScheduledReportListResponse>({
    queryKey: ["scheduled-reports"],
    queryFn: () => api.reports.listScheduled(),
    enabled: activeTab === "schedules",
  });

  // 4. Generate Mutation
  const generateMutation = useMutation({
    mutationFn: (payload: ReportGenerateRequest) => api.reports.generate(payload),
    onSuccess: (newReport) => {
      setIsGenerateModalOpen(false);
      setFeedbackMessage({
        type: "success",
        text: `Report "${newReport.title}" created successfully! PDF is ready.`,
      });
      queryClient.invalidateQueries({ queryKey: ["reports-list"] });
      setViewingReport(newReport);
      setTimeout(() => setFeedbackMessage(null), 6000);
    },
    onError: (err: Error) => {
      setFeedbackMessage({
        type: "error",
        text: `Failed to generate report: ${err.message}`,
      });
      setTimeout(() => setFeedbackMessage(null), 6000);
    },
  });

  // 5. Create Schedule Mutation
  const scheduleMutation = useMutation({
    mutationFn: (payload: ScheduledReportCreateRequest) => api.reports.createScheduled(payload),
    onSuccess: () => {
      setIsScheduleModalOpen(false);
      setFeedbackMessage({
        type: "success",
        text: "Automated report schedule created successfully.",
      });
      queryClient.invalidateQueries({ queryKey: ["scheduled-reports"] });
      setTimeout(() => setFeedbackMessage(null), 6000);
    },
    onError: (err: Error) => {
      setFeedbackMessage({
        type: "error",
        text: `Failed to create schedule: ${err.message}`,
      });
      setTimeout(() => setFeedbackMessage(null), 6000);
    },
  });

  // 6. Delete Schedule Mutation
  const deleteScheduleMutation = useMutation({
    mutationFn: (id: string) => api.reports.deleteScheduled(id),
    onSuccess: () => {
      setFeedbackMessage({
        type: "success",
        text: "Report schedule deleted.",
      });
      queryClient.invalidateQueries({ queryKey: ["scheduled-reports"] });
      setTimeout(() => setFeedbackMessage(null), 6000);
    },
  });

  // 7. Toggle Schedule Enabled
  const toggleScheduleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.reports.updateScheduled(id, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduled-reports"] });
    },
  });

  const handleGenerateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: ReportGenerateRequest = {
      report_type: genType,
      repository_id: genRepoId ? genRepoId : undefined,
      time_range: genTimeRange,
      start_date: genTimeRange === "custom" && genCustomStart ? new Date(genCustomStart).toISOString() : undefined,
      end_date: genTimeRange === "custom" && genCustomEnd ? new Date(genCustomEnd).toISOString() : undefined,
      title: genTitle.trim() || undefined,
      include_ai_insights: genIncludeAI,
      format: "pdf",
    };
    generateMutation.mutate(payload);
  };

  const handleScheduleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const emails = schedRecipients
      .split(",")
      .map((em) => em.trim())
      .filter((em) => em.length > 0);

    const payload: ScheduledReportCreateRequest = {
      report_type: schedType,
      repository_id: schedRepoId ? schedRepoId : undefined,
      frequency: schedFreq,
      timezone: schedTimezone,
      recipients: emails,
      enabled: true,
    };
    scheduleMutation.mutate(payload);
  };

  const formatReportType = (t: string) => {
    switch (t) {
      case "ENGINEERING_HEALTH":
        return "Engineering Health";
      case "WEEKLY":
        return "Weekly Retrospective";
      case "MONTHLY":
        return "Monthly Engineering";
      case "REPOSITORY_HEALTH":
        return "Repository Health";
      case "DORA":
        return "DORA Performance";
      default:
        return t.replace(/_/g, " ");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-3 w-3" /> Ready
          </span>
        );
      case "GENERATING":
      case "PENDING":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
            <Clock className="h-3 w-3 animate-spin" /> Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-600 dark:text-rose-400">
            <AlertCircle className="h-3 w-3" /> Failed
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Engineering Reports
            </h1>
            <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold uppercase text-primary">
              PDF Engine & Insights
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Enterprise health assessments, weekly and monthly retrospectives, DORA evaluations, and AI executive summaries.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsScheduleModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
          >
            <Clock className="h-4 w-4 text-muted-foreground" />
            Schedule
          </button>
          <button
            onClick={() => setIsGenerateModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Generate Report
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedbackMessage && (
        <div
          className={cn(
            "flex items-center justify-between rounded-lg p-4 text-sm font-medium",
            feedbackMessage.type === "success"
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20"
              : "bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20"
          )}
        >
          <span>{feedbackMessage.text}</span>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="rounded p-1 hover:bg-secondary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab("reports")}
            className={cn(
              "flex items-center gap-2 border-b-2 py-3 text-sm font-medium transition-colors",
              activeTab === "reports"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
            )}
          >
            <FileText className="h-4 w-4" />
            Generated Reports ({reportsData?.total ?? 0})
          </button>
          <button
            onClick={() => setActiveTab("schedules")}
            className={cn(
              "flex items-center gap-2 border-b-2 py-3 text-sm font-medium transition-colors",
              activeTab === "schedules"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
            )}
          >
            <Clock className="h-4 w-4" />
            Automated Schedules ({schedulesData?.total ?? 0})
          </button>
        </nav>
      </div>

      {/* Tab 1: Generated Reports */}
      {activeTab === "reports" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mr-1">
                <SlidersHorizontal className="h-3.5 w-3.5" /> Filters:
              </span>

              {/* Type Filter */}
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Report Types</option>
                <option value="ENGINEERING_HEALTH">Engineering Health</option>
                <option value="WEEKLY">Weekly Retrospective</option>
                <option value="MONTHLY">Monthly Engineering</option>
                <option value="REPOSITORY_HEALTH">Repository Health</option>
                <option value="DORA">DORA Report</option>
              </select>

              {/* Repo Filter */}
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

              {/* Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="all">All Statuses</option>
                <option value="COMPLETED">Ready</option>
                <option value="PENDING">Processing</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>

            <button
              onClick={() => refetchReports()}
              disabled={isReportsRefetching}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              <RefreshCw
                className={cn("h-3 w-3", isReportsRefetching && "animate-spin")}
              />
              Refresh
            </button>
          </div>

          {/* Reports Table / List */}
          {isReportsLoading ? (
            <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-card">
              <div className="flex flex-col items-center gap-2">
                <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                <p className="text-xs text-muted-foreground">Loading reports index...</p>
              </div>
            </div>
          ) : reportsData?.items && reportsData.items.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-secondary/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Report Title & Type</th>
                    <th className="px-4 py-3 font-semibold">Scope & Repository</th>
                    <th className="px-4 py-3 font-semibold">Reporting Period</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold">Generated</th>
                    <th className="px-4 py-3 text-right font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {reportsData.items.map((report) => {
                    const repoName =
                      repositories?.find((r) => r.id === report.repository_id)?.name ||
                      "Organization Wide";
                    const isAiPowered =
                      report.metadata_payload?.ai_insights_included ?? false;

                    return (
                      <tr
                        key={report.id}
                        className="hover:bg-secondary/20 transition-colors"
                      >
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2.5">
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div>
                              <div className="flex items-center gap-1.5 font-medium text-foreground">
                                <span>{report.title}</span>
                                {isAiPowered && (
                                  <span className="inline-flex items-center gap-0.5 rounded bg-purple-500/10 px-1 py-0.5 text-[10px] font-semibold text-purple-600 dark:text-purple-400">
                                    <Sparkles className="h-2.5 w-2.5" /> AI
                                  </span>
                                )}
                              </div>
                              <span className="text-[11px] text-muted-foreground">
                                {formatReportType(report.report_type)}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="px-4 py-3.5 text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {repoName}
                          </span>
                        </td>

                        <td className="px-4 py-3.5 text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>
                              {new Date(report.reporting_period_start).toLocaleDateString()}{" "}
                              –{" "}
                              {new Date(report.reporting_period_end).toLocaleDateString()}
                            </span>
                          </div>
                        </td>

                        <td className="px-4 py-3.5">{getStatusBadge(report.status)}</td>

                        <td className="px-4 py-3.5 text-muted-foreground">
                          {report.generated_at
                            ? new Date(report.generated_at).toLocaleString()
                            : "—"}
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => setViewingReport(report)}
                              className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground hover:bg-secondary transition-colors"
                            >
                              <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                              View
                            </button>
                            {report.status === "COMPLETED" && (
                              <a
                                href={api.reports.getDownloadUrl(report.id)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
                              >
                                <Download className="h-3.5 w-3.5" />
                                PDF
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="No Reports Generated Yet"
              description="Compile on-demand engineering retrospectives, monthly health assessments, or DORA evaluations with grounded AI summaries."
              actionText="Generate First Report"
              onAction={() => setIsGenerateModalOpen(true)}
              badge="Reporting Engine"
            />
          )}
        </div>
      )}

      {/* Tab 2: Automated Schedules */}
      {activeTab === "schedules" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Automated report crons run on the Celery beat worker and deliver executive summaries and downloadable PDFs to recipients.
            </p>
            <button
              onClick={() => setIsScheduleModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" /> Add Schedule
            </button>
          </div>

          {isSchedulesLoading ? (
            <div className="flex h-48 items-center justify-center rounded-lg border border-border bg-card">
              <RefreshCw className="h-5 w-5 animate-spin text-primary" />
            </div>
          ) : schedulesData?.items && schedulesData.items.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {schedulesData.items.map((sched) => {
                const repoName =
                  repositories?.find((r) => r.id === sched.repository_id)?.name ||
                  "Entire Organization";

                return (
                  <div
                    key={sched.id}
                    className="flex flex-col justify-between rounded-lg border border-border bg-card p-4 shadow-sm"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="inline-block rounded bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
                            {sched.frequency}
                          </span>
                          <h3 className="text-sm font-semibold text-foreground mt-1.5">
                            {formatReportType(sched.report_type)}
                          </h3>
                        </div>
                        <label className="relative inline-flex cursor-pointer items-center">
                          <input
                            type="checkbox"
                            checked={sched.enabled}
                            onChange={(e) =>
                              toggleScheduleMutation.mutate({
                                id: sched.id,
                                enabled: e.target.checked,
                              })
                            }
                            className="peer sr-only"
                          />
                          <div className="h-5 w-9 rounded-full bg-secondary peer peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all" />
                        </label>
                      </div>

                      <div className="space-y-1 text-xs text-muted-foreground">
                        <p>
                          <span className="font-medium text-foreground">Scope:</span>{" "}
                          {repoName}
                        </p>
                        <p>
                          <span className="font-medium text-foreground">Timezone:</span>{" "}
                          {sched.timezone}
                        </p>
                        <p>
                          <span className="font-medium text-foreground">Next Run:</span>{" "}
                          {new Date(sched.next_run_at).toLocaleString()}
                        </p>
                      </div>

                      {sched.recipients.length > 0 && (
                        <div className="border-t border-border pt-2">
                          <div className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground mb-1">
                            <Mail className="h-3 w-3" />
                            Recipients ({sched.recipients.length})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {sched.recipients.map((email, idx) => (
                              <span
                                key={idx}
                                className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-foreground"
                              >
                                {email}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 flex items-center justify-end border-t border-border pt-3">
                      <button
                        onClick={() => deleteScheduleMutation.mutate(sched.id)}
                        className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-700 dark:text-rose-400 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={Clock}
              title="No Scheduled Reports"
              description="Configure automatic weekly or monthly report generation to compile retrospectives on a cadence."
              actionText="Create First Schedule"
              onAction={() => setIsScheduleModalOpen(true)}
              badge="Automated Crons"
            />
          )}
        </div>
      )}

      {/* Modal: Generate Report */}
      {isGenerateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-bold text-foreground">
                  Generate Engineering Report
                </h2>
              </div>
              <button
                onClick={() => setIsGenerateModalOpen(false)}
                className="rounded p-1 text-muted-foreground hover:bg-secondary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleGenerateSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Report Type
                </label>
                <select
                  value={genType}
                  onChange={(e) =>
                    setGenType(
                      e.target.value as ReportGenerateRequest["report_type"]
                    )
                  }
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="ENGINEERING_HEALTH">
                    Engineering Health Report (Comprehensive Organization Overview)
                  </option>
                  <option value="WEEKLY">
                    Weekly Engineering Report (Throughput, Bottlenecks & Turnaround)
                  </option>
                  <option value="MONTHLY">
                    Monthly Engineering Report (Strategic Delivery & DORA Trends)
                  </option>
                  <option value="REPOSITORY_HEALTH">
                    Repository Health Report (Deep-dive on Single Codebase)
                  </option>
                  <option value="DORA">
                    DORA Metrics Report (4 Pillars, Elite Benchmarks & Provenance)
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Repository Scope
                </label>
                <select
                  value={genRepoId}
                  onChange={(e) => setGenRepoId(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Monitored Repositories (Organization)</option>
                  {repositories?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Time Window
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["7d", "14d", "30d", "90d", "custom"] as const).map((r) => (
                    <button
                      type="button"
                      key={r}
                      onClick={() => setGenTimeRange(r)}
                      className={cn(
                        "rounded-md border py-1.5 text-xs font-medium transition-colors",
                        genTimeRange === r
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border bg-background text-muted-foreground hover:bg-secondary"
                      )}
                    >
                      {r === "7d"
                        ? "7 Days"
                        : r === "14d"
                        ? "14 Days"
                        : r === "30d"
                        ? "30 Days"
                        : r === "90d"
                        ? "90 Days"
                        : "Custom"}
                    </button>
                  ))}
                </div>

                {genTimeRange === "custom" && (
                  <div className="mt-2.5 grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[11px] text-muted-foreground mb-1">
                        Start Date
                      </label>
                      <input
                        type="date"
                        value={genCustomStart}
                        onChange={(e) => setGenCustomStart(e.target.value)}
                        className="w-full rounded border border-border bg-background px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-muted-foreground mb-1">
                        End Date
                      </label>
                      <input
                        type="date"
                        value={genCustomEnd}
                        onChange={(e) => setGenCustomEnd(e.target.value)}
                        className="w-full rounded border border-border bg-background px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Custom Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Sprint Retrospective"
                  value={genTitle}
                  onChange={(e) => setGenTitle(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="rounded-lg border border-border bg-secondary/30 p-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={genIncludeAI}
                    onChange={(e) => setGenIncludeAI(e.target.checked)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                    <Sparkles className="h-3.5 w-3.5 text-purple-500" />
                    <span>Synthesize AI Insights & Executive Summary</span>
                  </div>
                </label>
                <p className="mt-1 text-[11px] text-muted-foreground pl-6">
                  Extracts verified telemetry, evaluates period-over-period deltas, and generates systemic workflow recommendations without inventing numbers.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsGenerateModalOpen(false)}
                  className="rounded-md border border-border px-3.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generateMutation.isPending}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
                >
                  {generateMutation.isPending ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      Generating Report...
                    </>
                  ) : (
                    <>
                      <FileText className="h-3.5 w-3.5" />
                      Generate & Render PDF
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Schedule Report */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-bold text-foreground">
                  Schedule Automated Report
                </h2>
              </div>
              <button
                onClick={() => setIsScheduleModalOpen(false)}
                className="rounded p-1 text-muted-foreground hover:bg-secondary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleScheduleSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Report Type
                </label>
                <select
                  value={schedType}
                  onChange={(e) =>
                    setSchedType(
                      e.target.value as ScheduledReportCreateRequest["report_type"]
                    )
                  }
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="WEEKLY">Weekly Engineering Report</option>
                  <option value="MONTHLY">Monthly Engineering Report</option>
                  <option value="ENGINEERING_HEALTH">Engineering Health Report</option>
                  <option value="DORA">DORA Performance Report</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Repository Scope
                </label>
                <select
                  value={schedRepoId}
                  onChange={(e) => setSchedRepoId(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Monitored Repositories</option>
                  {repositories?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">
                    Frequency
                  </label>
                  <select
                    value={schedFreq}
                    onChange={(e) =>
                      setSchedFreq(
                        e.target.value as ScheduledReportCreateRequest["frequency"]
                      )
                    }
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="WEEKLY">Weekly (Monday 00:00)</option>
                    <option value="MONTHLY">Monthly (1st of month)</option>
                    <option value="DAILY">Daily (00:00)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">
                    Timezone
                  </label>
                  <select
                    value={schedTimezone}
                    onChange={(e) => setSchedTimezone(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="UTC">UTC (Universal Time)</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                    <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Notification Recipients (comma-separated emails)
                </label>
                <input
                  type="text"
                  placeholder="lead@company.com, engineering-managers@company.com"
                  value={schedRecipients}
                  onChange={(e) => setSchedRecipients(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="rounded-md border border-border px-3.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduleMutation.isPending}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
                >
                  {scheduleMutation.isPending ? "Creating..." : "Confirm Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal / Drawer: Report Detail Viewer */}
      {viewingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="flex h-[90vh] w-full max-w-4xl flex-col rounded-xl border border-border bg-card shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-foreground">
                    {viewingReport.title}
                  </h2>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{formatReportType(viewingReport.report_type)}</span>
                    <span>•</span>
                    <span>
                      {new Date(viewingReport.reporting_period_start).toLocaleDateString()}{" "}
                      –{" "}
                      {new Date(viewingReport.reporting_period_end).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {viewingReport.status === "COMPLETED" && (
                  <a
                    href={api.reports.getDownloadUrl(viewingReport.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download PDF
                  </a>
                )}
                <button
                  onClick={() => setViewingReport(null)}
                  className="rounded p-1.5 text-muted-foreground hover:bg-secondary"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Sections List */}
              {viewingReport.sections && viewingReport.sections.length > 0 ? (
                viewingReport.sections.map((section, idx) => (
                  <div
                    key={section.id || idx}
                    className="rounded-lg border border-border bg-secondary/10 p-5 space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-border pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                          {idx + 1}
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          {section.title}
                        </h3>
                      </div>
                      <span className="text-[10px] uppercase font-semibold text-muted-foreground">
                        {section.section_type}
                      </span>
                    </div>

                    {/* Section Content rendering */}
                    {Boolean(section.content?.summary) && (
                      <p className="text-xs leading-relaxed text-foreground bg-card/60 rounded p-3 border border-border/50">
                        {String(section.content?.summary)}
                      </p>
                    )}

                    {/* Render content key-values if structured */}
                    {section.content && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                        {Object.entries(section.content)
                          .filter(([k]) => k !== "summary")
                          .map(([key, val]) => (
                            <div
                              key={key}
                              className="rounded border border-border/60 bg-card p-2 text-xs"
                            >
                              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                                {key.replace(/_/g, " ")}
                              </div>
                              <div className="font-semibold text-foreground truncate">
                                {typeof val === "object" ? JSON.stringify(val) : String(val)}
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No rendered sections recorded for this report.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
