import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { PullRequestsPage } from "@/pages/pull-requests/PullRequestsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>{ui}</BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

describe("Phase 4 Pull Request Analytics UI", () => {
  it("renders page title, subtitle, and Anti-Surveillance commitment banner", () => {
    renderWithProviders(<PullRequestsPage />);

    expect(screen.getByText("Pull Request Analytics")).toBeInTheDocument();
    expect(screen.getByText("Flow & Throughput")).toBeInTheDocument();
    expect(
      screen.getByText(/End-to-end pull request lifecycle velocity, review latencies, and size distributions/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anti-Surveillance Commitment/i)).toBeInTheDocument();
  });

  it("renders filter bar, repository dropdown, and sync button", () => {
    renderWithProviders(<PullRequestsPage />);

    expect(screen.getByText("All Monitored Repositories")).toBeInTheDocument();
    expect(screen.getByText("7d")).toBeInTheDocument();
    expect(screen.getByText("14d")).toBeInTheDocument();
    expect(screen.getByText("30d")).toBeInTheDocument();
    expect(screen.getByText("90d")).toBeInTheDocument();
    expect(screen.getByText("Sync PRs")).toBeInTheDocument();
  });

  it("renders KPI cards and size distribution section", () => {
    renderWithProviders(<PullRequestsPage />);

    expect(screen.getByText("PR Merge Rate")).toBeInTheDocument();
    expect(screen.getByText("Median Merge Time (P50)")).toBeInTheDocument();
    expect(screen.getByText("Median Cycle Time")).toBeInTheDocument();
    expect(screen.getByText("Currently Open")).toBeInTheDocument();

    expect(screen.getByText("Small (under 100 lines)")).toBeInTheDocument();
    expect(screen.getByText("Medium (100 to 500 lines)")).toBeInTheDocument();
    expect(screen.getByText("Large (over 500 lines)")).toBeInTheDocument();
  });
});
