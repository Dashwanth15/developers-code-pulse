/**
 * Developers Code Pulse (DCP) - API Client
 * Robust, typed HTTP client with automatic JWT token management and organization context headers.
 */

const API_BASE_URL = "/api/v1";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
  memberships: OrganizationMemberResponse[];
}

export interface OrganizationMemberResponse {
  id: string;
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  refresh_token: string;
}

export interface DiscoveredRepo {
  github_repo_id: number;
  name: string;
  full_name: string;
  default_branch: string;
  is_private: boolean;
  primary_language: string | null;
  html_url: string;
  is_connected: boolean;
}

export interface ConnectedRepository {
  id: string;
  organization_id: string;
  github_repo_id: number;
  name: string;
  full_name: string;
  default_branch: string;
  is_private: boolean;
  is_monitored: boolean;
  primary_language: string | null;
  last_synced_at: string | null;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, message: string, code = "UNKNOWN_ERROR") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("dcp_access_token");
  const orgId = localStorage.getItem("dcp_active_org_id");

  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (orgId) {
    headers.set("X-Organization-ID", orgId);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred.";
    let errorCode = "HTTP_ERROR";

    try {
      const errData = await response.json();
      errorDetail = errData.detail || errData.title || errorDetail;
      errorCode = errData.code || errorCode;
    } catch {
      // Non-json response
    }

    throw new ApiError(response.status, errorDetail, errorCode);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    login: async (credentials: { email: string; password: string }): Promise<TokenResponse> => {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(res.status, err.detail || "Invalid credentials", err.code || "AUTH_FAILED");
      }
      return res.json();
    },

    register: async (payload: {
      email: string;
      password: string;
      full_name: string;
      organization_name?: string;
    }): Promise<TokenResponse> => {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(res.status, err.detail || "Registration failed", err.code || "REGISTRATION_FAILED");
      }
      return res.json();
    },

    getMe: (): Promise<UserResponse> => {
      return fetchWithAuth<UserResponse>("/auth/me");
    },

    logout: async (): Promise<void> => {
      try {
        await fetchWithAuth("/auth/logout", { method: "POST" });
      } finally {
        localStorage.removeItem("dcp_access_token");
        localStorage.removeItem("dcp_refresh_token");
        localStorage.removeItem("dcp_active_org_id");
      }
    },
  },

  repositories: {
    list: (): Promise<ConnectedRepository[]> => {
      return fetchWithAuth<ConnectedRepository[]>("/repositories");
    },

    connect: (payload: {
      github_repo_id: number;
      name: string;
      full_name: string;
      default_branch?: string;
      is_private?: boolean;
      primary_language?: string | null;
    }): Promise<ConnectedRepository> => {
      return fetchWithAuth<ConnectedRepository[]>("/repositories", {
        method: "POST",
        body: JSON.stringify(payload),
      }) as unknown as Promise<ConnectedRepository>;
    },

    toggleMonitoring: (repoId: string, is_monitored: boolean): Promise<ConnectedRepository> => {
      return fetchWithAuth<ConnectedRepository>(`/repositories/${repoId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_monitored }),
      });
    },

    getCommits: (
      repoId: string,
      params?: { limit?: number; offset?: number; branch?: string }
    ): Promise<CommitDetail[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.offset) searchParams.set("offset", params.offset.toString());
      if (params?.branch) searchParams.set("branch", params.branch);
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<CommitDetail[]>(`/repositories/${repoId}/commits${query}`);
    },

    syncCommits: (repoId: string): Promise<{ status: string; synced_commits: number }> => {
      return fetchWithAuth<{ status: string; synced_commits: number }>(
        `/repositories/${repoId}/sync-commits`,
        { method: "POST" }
      );
    },

    getPullRequests: (
      repoId: string,
      params?: { limit?: number; offset?: number; state?: string }
    ): Promise<PullRequestDetail[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.offset) searchParams.set("offset", params.offset.toString());
      if (params?.state) searchParams.set("state", params.state);
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<PullRequestDetail[]>(`/repositories/${repoId}/pull-requests${query}`);
    },

    syncPullRequests: (repoId: string): Promise<{ status: string; synced_pull_requests: number }> => {
      return fetchWithAuth<{ status: string; synced_pull_requests: number }>(
        `/repositories/${repoId}/sync-prs`,
        { method: "POST" }
      );
    },
  },

  github: {
    discover: (): Promise<DiscoveredRepo[]> => {
      return fetchWithAuth<DiscoveredRepo[]>("/integrations/github/repositories");
    },
  },

  analytics: {
    getCommits: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<CommitAnalyticsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<CommitAnalyticsResponse>(`/analytics/commits${query}`);
    },

    getPullRequests: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<PRAnalyticsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<PRAnalyticsResponse>(`/analytics/pull-requests${query}`);
    },

    getReviews: (params?: {
      repository_ids?: string[];
      time_window?: string;
    }): Promise<ReviewAnalyticsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<ReviewAnalyticsResponse>(`/analytics/reviews${query}`);
    },

    getReviewWorkload: (params?: {
      repository_ids?: string[];
      time_window?: string;
    }): Promise<ReviewWorkloadResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<ReviewWorkloadResponse>(`/analytics/reviews/workload${query}`);
    },

    getPendingReviews: (params?: {
      repository_ids?: string[];
    }): Promise<PendingReviewQueueResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<PendingReviewQueueResponse>(`/analytics/reviews/pending${query}`);
    },

    getTeamIntelligence: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<TeamIntelligenceResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<TeamIntelligenceResponse>(`/analytics/team${query}`);
    },

    getTeamTrends: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<TeamTrendsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<TeamTrendsResponse>(`/analytics/team/trends${query}`);
    },

    getDoraOverview: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<DORAOverviewResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<DORAOverviewResponse>(`/analytics/dora${query}`);
    },

    getDeploymentFrequency: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<DeploymentFrequencyDetail> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<DeploymentFrequencyDetail>(`/analytics/dora/deployment-frequency${query}`);
    },

    getLeadTime: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<LeadTimeDetail> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<LeadTimeDetail>(`/analytics/dora/lead-time${query}`);
    },

    getChangeFailureRate: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<ChangeFailureRateDetail> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<ChangeFailureRateDetail>(`/analytics/dora/change-failure-rate${query}`);
    },

    getMeanTimeToRecovery: (params?: {
      repository_ids?: string[];
      time_window?: string;
      start_date?: string;
      end_date?: string;
    }): Promise<RecoveryTimeDetail> => {
      const searchParams = new URLSearchParams();
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      if (params?.repository_ids && params.repository_ids.length > 0) {
        params.repository_ids.forEach((id) => searchParams.append("repository_ids", id));
      }
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<RecoveryTimeDetail>(`/analytics/dora/mean-time-to-recovery${query}`);
    },
  },

  pullRequests: {
    list: (params?: {
      repository_id?: string;
      state?: string;
      page?: number;
      size?: number;
    }): Promise<PullRequestListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      if (params?.state) searchParams.set("state", params.state);
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.size) searchParams.set("size", params.size.toString());
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<PullRequestListResponse>(`/pull-requests${query}`);
    },

    get: (id: string): Promise<PullRequestDetail> => {
      return fetchWithAuth<PullRequestDetail>(`/pull-requests/${id}`);
    },

    getReviews: (id: string): Promise<PRReviewDetail[]> => {
      return fetchWithAuth<PRReviewDetail[]>(`/pull-requests/${id}/reviews`);
    },
  },

  bottlenecks: {
    list: (params?: {
      repository_id?: string;
      severity?: string;
      bottleneck_type?: string;
      status?: string;
      page?: number;
      size?: number;
    }): Promise<BottleneckListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      if (params?.severity) searchParams.set("severity", params.severity);
      if (params?.bottleneck_type) searchParams.set("bottleneck_type", params.bottleneck_type);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.size) searchParams.set("size", params.size.toString());
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<BottleneckListResponse>(`/bottlenecks${query}`);
    },

    get: (id: string): Promise<BottleneckResponse> => {
      return fetchWithAuth<BottleneckResponse>(`/bottlenecks/${id}`);
    },

    getSummary: (params?: { repository_id?: string }): Promise<BottleneckSummaryResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<BottleneckSummaryResponse>(`/bottlenecks/summary${query}`);
    },

    getTrends: (params?: { repository_id?: string; time_window?: string }): Promise<BottleneckTrendsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      if (params?.time_window) searchParams.set("time_window", params.time_window);
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<BottleneckTrendsResponse>(`/bottlenecks/trends${query}`);
    },

    getRecommendations: (params?: { repository_id?: string }): Promise<BottleneckRecommendationsResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<BottleneckRecommendationsResponse>(`/bottlenecks/recommendations${query}`);
    },

    detect: (payload?: { repository_id?: string; time_window?: string }): Promise<DetectionRunResponse> => {
      return fetchWithAuth<DetectionRunResponse>("/bottlenecks/detect", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    },

    updateStatus: (id: string, status: string): Promise<BottleneckResponse> => {
      return fetchWithAuth<BottleneckResponse>(`/bottlenecks/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
    },
  },

  deployments: {
    list: (params?: {
      repository_id?: string;
      environment?: string;
      status?: string;
      page?: number;
      size?: number;
    }): Promise<DeploymentListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      if (params?.environment) searchParams.set("environment", params.environment);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.size) searchParams.set("size", params.size.toString());
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<DeploymentListResponse>(`/deployments${query}`);
    },

    create: (payload: DeploymentCreateRequest): Promise<DeploymentResponse> => {
      return fetchWithAuth<DeploymentResponse>("/deployments", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    sync: (payload?: { repository_id?: string; environment?: string }): Promise<SyncResultResponse> => {
      return fetchWithAuth<SyncResultResponse>("/deployments/sync", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    },
  },

  incidents: {
    list: (params?: {
      repository_id?: string;
      status?: string;
      severity?: string;
      page?: number;
      size?: number;
    }): Promise<IncidentListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.severity) searchParams.set("severity", params.severity);
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.size) searchParams.set("size", params.size.toString());
      const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
      return fetchWithAuth<IncidentListResponse>(`/incidents${query}`);
    },

    create: (payload: IncidentCreateRequest): Promise<IncidentResponse> => {
      return fetchWithAuth<IncidentResponse>("/incidents", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    sync: (payload?: { repository_id?: string; source?: string }): Promise<SyncResultResponse> => {
      return fetchWithAuth<SyncResultResponse>("/incidents/sync", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    },
  },
};

export interface CommitCadencePoint {
  date: string;
  commit_count: number;
  additions: number;
  deletions: number;
}

export interface CommitHeatmapPoint {
  day_of_week: number;
  hour_of_day: number;
  commit_count: number;
}

export interface CommitContributorSummary {
  author_id: string;
  login: string;
  name: string | null;
  avatar_url: string | null;
  commit_count: number;
  additions: number;
  deletions: number;
  last_committed_at: string;
}

export interface RepositoryCommitSummary {
  repository_id: string;
  name: string;
  commit_count: number;
  additions: number;
  deletions: number;
  active_contributors_count: number;
}

export interface CommitAnalyticsSummary {
  total_commits: number;
  daily_cadence: number;
  weekday_cadence: number;
  active_contributors: number;
  total_additions: number;
  total_deletions: number;
  total_churn: number;
  merge_commit_count: number;
}

export interface CommitAnalyticsResponse {
  time_window: string;
  start_date: string;
  end_date: string;
  summary: CommitAnalyticsSummary;
  cadence_trend: CommitCadencePoint[];
  heatmap: CommitHeatmapPoint[];
  top_contributors: CommitContributorSummary[];
  repository_comparison: RepositoryCommitSummary[];
}

export interface CommitDetail {
  id: string;
  repository_id: string;
  commit_sha: string;
  message: string;
  committed_at: string;
  additions: number;
  deletions: number;
  total_changes: number;
  branch_name: string;
  is_merge_commit: boolean;
  author: {
    id: string;
    login: string;
    name: string | null;
    avatar_url: string | null;
    user_type: string;
  } | null;
}

export interface PullRequestDetail {
  id: string;
  repository_id: string;
  github_pr_id: number;
  number: number;
  title: string;
  state: string; // 'OPEN' | 'CLOSED' | 'MERGED'
  is_draft: boolean;
  source_branch: string;
  target_branch: string;
  created_at_github: string;
  updated_at_github: string;
  closed_at: string | null;
  merged_at: string | null;
  first_reviewed_at: string | null;
  additions: number;
  deletions: number;
  changed_files: number;
  commit_count: number;
  cycle_time_seconds: number | null;
  merge_time_seconds: number | null;
  first_review_time_seconds: number | null;
  author_login: string | null;
  author_avatar: string | null;
}

export interface PRAnalyticsSummary {
  total_prs_opened: number;
  total_prs_merged: number;
  total_prs_closed_unmerged: number;
  currently_open_prs: number;
  merge_rate_percentage: number;
  median_merge_time_hours: number | null;
  p75_merge_time_hours: number | null;
  median_cycle_time_hours: number | null;
}

export interface PRCadenceTrendPoint {
  date: string;
  opened: number;
  merged: number;
  closed: number;
}

export interface PRSizeBucket {
  count: number;
  avg_merge_hours: number | null;
}

export interface PRSizeDistribution {
  small_under_100_lines: PRSizeBucket;
  medium_100_to_500_lines: PRSizeBucket;
  large_over_500_lines: PRSizeBucket;
}

export interface PRAnalyticsResponse {
  time_window: string;
  start_date: string;
  end_date: string;
  summary: PRAnalyticsSummary;
  cadence_trend: PRCadenceTrendPoint[];
  size_distribution: PRSizeDistribution;
}

export interface PullRequestListResponse {
  items: PullRequestDetail[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TTFRMetrics {
  median_hours: number | null;
  p75_hours: number | null;
  p90_hours: number | null;
  benchmark_comparison: string;
}

export interface ApprovalTurnaroundMetrics {
  median_hours: number | null;
  p75_hours: number | null;
}

export interface ReviewSummaryMetrics {
  time_to_first_review: TTFRMetrics;
  approval_turnaround: ApprovalTurnaroundMetrics;
  average_review_rounds: number;
  review_coverage_rate: number;
}

export interface TurnaroundHistogramBucket {
  range: string;
  count: number;
}

export interface ReviewAnalyticsResponse {
  time_window: string;
  start_date: string;
  end_date: string;
  metrics: ReviewSummaryMetrics;
  turnaround_histogram: TurnaroundHistogramBucket[];
  pending_queue_count: number;
}

export interface ReviewerWorkloadItem {
  account_id: string;
  login: string;
  name: string | null;
  avatar_url: string | null;
  reviews_conducted: number;
  approvals_given: number;
  changes_requested: number;
  review_share_percentage: number;
}

export interface ReviewWorkloadResponse {
  time_window: string;
  gini_coefficient: number;
  workload_balance_status: string; // 'BALANCED' | 'MODERATE' | 'UNBALANCED'
  total_reviews: number;
  reviewers: ReviewerWorkloadItem[];
}

export interface PendingReviewItem {
  pull_request_id: string;
  number: number;
  title: string;
  repository_name: string;
  author_login: string | null;
  author_avatar: string | null;
  waiting_hours: number;
  created_at: string;
  requested_reviewers: string[];
}

export interface PendingReviewQueueResponse {
  total_pending: number;
  items: PendingReviewItem[];
}

export interface PRReviewDetail {
  id: string;
  pull_request_id: string;
  reviewer_account_id: string | null;
  reviewer_login: string | null;
  reviewer_avatar: string | null;
  state: string; // 'APPROVED' | 'CHANGES_REQUESTED' | 'COMMENTED' | 'DISMISSED'
  submitted_at: string;
  commit_sha: string | null;
}

export interface BottleneckResponse {
  id: string;
  organization_id: string;
  repository_id: string | null;
  repository_name: string | null;
  bottleneck_type: string;
  severity: string; // 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  confidence: string; // 'LOW' | 'MEDIUM' | 'HIGH'
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  recommendation: string;
  detected_at: string;
  first_observed_at: string;
  last_observed_at: string;
  status: string; // 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'IGNORED'
  fingerprint: string;
  resolved_at: string | null;
}

export interface BottleneckListResponse {
  items: BottleneckResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface BottleneckSummaryResponse {
  total_active: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  affected_repositories_count: number;
  resolved_count: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
}

export interface BottleneckTrendPoint {
  date: string;
  active_count: number;
  detected_count: number;
  resolved_count: number;
}

export interface BottleneckTrendsResponse {
  time_window: string;
  trends: BottleneckTrendPoint[];
}

export interface BottleneckRecommendationItem {
  bottleneck_type: string;
  title: string;
  recommendation: string;
  severity: string;
  impact: string;
  affected_repositories: string[];
  evidence_summary: string;
}

export interface BottleneckRecommendationsResponse {
  total_recommendations: number;
  recommendations: BottleneckRecommendationItem[];
}

export interface DetectionRunResponse {
  run_id: string;
  status: string;
  organization_id: string;
  repository_id: string | null;
  total_bottlenecks: number;
  started_at: string;
  completed_at: string | null;
  message: string | null;
}

// ==============================================================================
// Phase 7: Team Intelligence & DORA Metrics Interfaces
// ==============================================================================

export interface DORAMetricCard {
  metric_type: string;
  title: string;
  status: "CALCULATED" | "INSUFFICIENT_DATA" | "REQUIRES_INTEGRATION";
  value: number | null;
  formatted_value: string;
  unit: string;
  performance_level: "ELITE" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  performance_label: string;
  trend_direction: "IMPROVED" | "DEGRADED" | "STABLE" | "NONE";
  trend_percentage: number | null;
  sample_size: number;
  data_completeness: number;
  period: string;
  data_source: string;
  methodology: string;
  context_message: string | null;
}

export interface DORATrendPoint {
  date: string;
  value: number | null;
  sample_size: number;
}

export interface DeploymentFrequencyDetail {
  card: DORAMetricCard;
  daily_deployments: number;
  weekly_deployments: number;
  monthly_deployments: number;
  total_deployments: number;
  successful_deployments: number;
  failed_deployments: number;
  history: DORATrendPoint[];
  environment_breakdown: Record<string, number>;
}

export interface LeadTimeDetail {
  card: DORAMetricCard;
  median_hours: number | null;
  p75_hours: number | null;
  average_hours: number | null;
  commit_to_merge_hours: number | null;
  merge_to_deploy_hours: number | null;
  sample_size: number;
  traceability_rate: number;
  history: DORATrendPoint[];
}

export interface ChangeFailureRateDetail {
  card: DORAMetricCard;
  failure_rate_percent: number | null;
  total_production_deployments: number;
  failed_deployments: number;
  incident_linked_deployments: number;
  degraded_deployments: number;
  history: DORATrendPoint[];
}

export interface RecoveryTimeDetail {
  card: DORAMetricCard;
  median_hours: number | null;
  p75_hours: number | null;
  average_hours: number | null;
  total_incidents: number;
  resolved_incidents: number;
  open_incidents: number;
  history: DORATrendPoint[];
}

export interface RepositoryDORAOverview {
  repository_id: string;
  repository_name: string;
  deployment_frequency: DORAMetricCard;
  lead_time: DORAMetricCard;
  change_failure_rate: DORAMetricCard;
  mean_time_to_recovery: DORAMetricCard;
}

export interface DORAOverviewResponse {
  organization_id: string;
  time_window: string;
  start_date: string;
  end_date: string;
  overall_performance: "ELITE" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  deployment_frequency: DORAMetricCard;
  lead_time_for_changes: DORAMetricCard;
  change_failure_rate: DORAMetricCard;
  mean_time_to_recovery: DORAMetricCard;
  repository_breakdowns: RepositoryDORAOverview[];
  integration_status: {
    github_actions: boolean;
    github_deployments: boolean;
    incident_system: boolean;
  };
}

export interface DeploymentResponse {
  id: string;
  organization_id: string;
  repository_id: string | null;
  repository_name: string | null;
  external_deployment_id: string | null;
  environment: string;
  status: string;
  deployed_at: string;
  completed_at: string | null;
  commit_sha: string | null;
  ref_name: string | null;
  source: string;
  lead_time_seconds: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DeploymentListResponse {
  items: DeploymentResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface DeploymentCreateRequest {
  repository_id?: string;
  external_deployment_id?: string;
  environment?: string;
  status?: string;
  deployed_at: string;
  completed_at?: string;
  commit_sha?: string;
  ref_name?: string;
  source?: string;
  lead_time_seconds?: number;
  metadata?: Record<string, unknown>;
}

export interface IncidentResponse {
  id: string;
  organization_id: string;
  repository_id: string | null;
  repository_name: string | null;
  external_incident_id: string | null;
  title: string;
  severity: string;
  status: string;
  started_at: string;
  resolved_at: string | null;
  recovery_duration_seconds: number | null;
  source: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface IncidentListResponse {
  items: IncidentResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface IncidentCreateRequest {
  repository_id?: string;
  external_incident_id?: string;
  title: string;
  severity?: string;
  status?: string;
  started_at: string;
  resolved_at?: string;
  source?: string;
  deployment_id?: string;
  metadata?: Record<string, unknown>;
}

export interface SyncResultResponse {
  synced_count: number;
  status: string;
  message: string;
}

export interface MacroThroughput {
  total_prs_opened: number;
  total_prs_merged: number;
  total_prs_closed: number;
  merge_rate_percent: number;
  total_commits: number;
  total_reviews: number;
}

export interface DeliveryCadence {
  deployments_count: number;
  median_lead_time_hours: number | null;
  median_review_turnaround_hours: number | null;
  median_merge_latency_hours: number | null;
}

export interface BottleneckDistributionSummary {
  total_active: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_type: Record<string, number>;
}

export interface CollaborationPattern {
  multi_reviewer_pr_rate: number;
  cross_repo_collaboration_index: number;
  average_review_comments_per_pr: number;
  review_coverage_rate: number;
}

export interface RepoDeliveryTrend {
  repository_id: string;
  repository_name: string;
  pr_throughput: number;
  merge_rate: number;
  median_cycle_time_hours: number | null;
  deployment_count: number;
  active_bottlenecks: number;
}

export interface TeamTrendSeriesPoint {
  date: string;
  prs_opened: number;
  prs_merged: number;
  reviews_completed: number;
  deployments: number;
}

export interface TeamIntelligenceResponse {
  organization_id: string;
  time_window: string;
  start_date: string;
  end_date: string;
  anti_surveillance_notice: string;
  throughput: MacroThroughput;
  delivery_cadence: DeliveryCadence;
  bottlenecks: BottleneckDistributionSummary;
  collaboration: CollaborationPattern;
  repository_trends: RepoDeliveryTrend[];
  systemic_recommendations: Array<{
    category: string;
    title: string;
    observation: string;
    suggestion: string;
  }>;
}

export interface TeamTrendsResponse {
  organization_id: string;
  time_window: string;
  series: TeamTrendSeriesPoint[];
}


