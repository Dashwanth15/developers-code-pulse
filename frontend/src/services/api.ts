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
