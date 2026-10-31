import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { CommitsPage } from "@/pages/commits/CommitsPage";

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

describe("Phase 3 Commit Intelligence UI", () => {
  it("renders page title and Anti-Surveillance commitment banner", () => {
    renderWithProviders(<CommitsPage />);

    expect(screen.getByText("Commit Intelligence")).toBeInTheDocument();
    expect(
      screen.getByText(/Observe engineering velocity rhythm, commit cadence, and team participation patterns/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anti-Surveillance Commitment/i)).toBeInTheDocument();
  });

  it("renders filter bar with repository dropdown and time window options", () => {
    renderWithProviders(<CommitsPage />);

    expect(screen.getByText("All Monitored Repositories")).toBeInTheDocument();
    expect(screen.getByText("7d")).toBeInTheDocument();
    expect(screen.getByText("14d")).toBeInTheDocument();
    expect(screen.getByText("30d")).toBeInTheDocument();
    expect(screen.getByText("90d")).toBeInTheDocument();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });
});
