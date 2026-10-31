import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { BottlenecksPage } from "@/pages/bottlenecks/BottlenecksPage";

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

describe("Phase 6 Bottleneck Detection UI", () => {
  it("renders page title, intelligence engine badge, and Anti-Surveillance commitment banner", () => {
    renderWithProviders(<BottlenecksPage />);

    expect(screen.getByText("Bottleneck Detection Engine")).toBeInTheDocument();
    expect(screen.getByText("Intelligence Engine")).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic identification of workflow delivery friction, review lag, and reviewer capacity congestion/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anti-Surveillance Commitment:/i)).toBeInTheDocument();
  });

  it("renders filter toolbar, repository dropdown, and manual detection button", () => {
    renderWithProviders(<BottlenecksPage />);

    expect(screen.getByText("All Repositories")).toBeInTheDocument();
    expect(screen.getByText("Run Detection")).toBeInTheDocument();
    expect(screen.getByText("Refresh")).toBeInTheDocument();
  });

  it("renders the 4 overview KPI cards", () => {
    renderWithProviders(<BottlenecksPage />);

    expect(screen.getByText("Active Bottlenecks")).toBeInTheDocument();
    expect(screen.getByText("Critical & High")).toBeInTheDocument();
    expect(screen.getByText("Affected Repositories")).toBeInTheDocument();
    expect(screen.getByText("Resolved Bottlenecks")).toBeInTheDocument();
  });

  it("renders actionable flow guidance and severity distribution panels", () => {
    renderWithProviders(<BottlenecksPage />);

    expect(screen.getByText("Actionable Flow Guidance")).toBeInTheDocument();
    expect(screen.getByText("Bottlenecks by Severity")).toBeInTheDocument();
  });
});
