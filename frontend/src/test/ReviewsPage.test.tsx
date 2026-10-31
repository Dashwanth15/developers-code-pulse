import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { ReviewsPage } from "@/pages/reviews/ReviewsPage";

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

describe("Phase 5 Review Intelligence UI", () => {
  it("renders page title, signature badge, and Anti-Surveillance commitment banner", () => {
    renderWithProviders(<ReviewsPage />);

    expect(screen.getByText("Review Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Signature Feature")).toBeInTheDocument();
    expect(
      screen.getByText(/Turnaround latency percentiles, peer review coverage, and team workload dispersion/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anti-Surveillance Commitment:/i)).toBeInTheDocument();
  });

  it("renders filter toolbar with time window buttons and repository selector", () => {
    renderWithProviders(<ReviewsPage />);

    expect(screen.getByText("7d")).toBeInTheDocument();
    expect(screen.getByText("14d")).toBeInTheDocument();
    expect(screen.getByText("30d")).toBeInTheDocument();
    expect(screen.getByText("90d")).toBeInTheDocument();
    expect(screen.getByText("All Repositories")).toBeInTheDocument();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });

  it("renders the 4 primary KPI cards", () => {
    renderWithProviders(<ReviewsPage />);

    expect(screen.getByText("Time to First Review")).toBeInTheDocument();
    expect(screen.getByText("Approval Turnaround")).toBeInTheDocument();
    expect(screen.getByText("Review Coverage")).toBeInTheDocument();
    expect(screen.getByText("Pending Queue (≥12h)")).toBeInTheDocument();
  });

  it("renders turnaround histogram and workload balance matrix", () => {
    renderWithProviders(<ReviewsPage />);

    expect(screen.getByText("Turnaround Latency Distribution")).toBeInTheDocument();
    expect(screen.getByText("Reviewer Workload Balance Matrix")).toBeInTheDocument();
    expect(screen.getByText("Gini Concentration Index")).toBeInTheDocument();
    expect(screen.getByText("Urgent Pending Review Queue")).toBeInTheDocument();
  });
});
