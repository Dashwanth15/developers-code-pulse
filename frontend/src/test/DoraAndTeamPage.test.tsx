import React from "react";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { DoraPage } from "@/pages/dora/DoraPage";
import { TeamInsightsPage } from "@/pages/team-insights/TeamInsightsPage";

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

describe("Phase 7 DORA Metrics UI", () => {
  it("renders page title and subtitle", () => {
    renderWithProviders(<DoraPage />);

    expect(screen.getByText("DORA Delivery Metrics")).toBeInTheDocument();
    expect(
      screen.getByText(/Industry standard four software delivery performance pillars/i)
    ).toBeInTheDocument();
  });

  it("renders the 4 primary DORA metric cards", () => {
    renderWithProviders(<DoraPage />);

    expect(screen.getAllByText("Deployment Frequency").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Lead Time for Changes").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Change Failure Rate").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Time to Restore Service").length).toBeGreaterThanOrEqual(1);
  });

  it("renders source integration badges and target repository filter", () => {
    renderWithProviders(<DoraPage />);

    expect(screen.getByText("Target Repository:")).toBeInTheDocument();
    expect(screen.getByText("All Connected Repositories")).toBeInTheDocument();
    expect(screen.getByText("GitHub Actions")).toBeInTheDocument();
    expect(screen.getByText(/Sync Deployments/i)).toBeInTheDocument();
  });

  it("renders sub-navigation tabs for trends, rollouts, and methodology", () => {
    renderWithProviders(<DoraPage />);

    expect(screen.getByText("Trends & Repository Comparison")).toBeInTheDocument();
    expect(screen.getByText(/Production Rollouts Log/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculation Methodology & Integrity/i)).toBeInTheDocument();
  });
});

describe("Phase 7 Team Intelligence UI", () => {
  it("renders page title, subtitle, and strict Anti-Surveillance commitment banner", () => {
    renderWithProviders(<TeamInsightsPage />);

    expect(screen.getByText("Team Intelligence & Delivery Flow")).toBeInTheDocument();
    expect(
      screen.getByText(/Macro-level delivery cadence, peer review dynamics, and system flow/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Anti-Surveillance Privacy Charter & Ethics Guarantee/i)).toBeInTheDocument();
    expect(screen.getByText("ZERO INDIVIDUAL RANKINGS")).toBeInTheDocument();
  });

  it("renders macro throughput KPI cards", () => {
    renderWithProviders(<TeamInsightsPage />);

    expect(screen.getAllByText("PRs Opened").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("PRs Merged").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Merge Rate").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Peer Reviews")).toBeInTheDocument();
    expect(screen.getByText("Code Commits")).toBeInTheDocument();
    expect(screen.getAllByText("Production Deploys").length).toBeGreaterThanOrEqual(1);
  });

  it("renders delivery speed and collaboration health cards", () => {
    renderWithProviders(<TeamInsightsPage />);

    expect(screen.getByText("Macro Delivery Speed & Latencies")).toBeInTheDocument();
    expect(screen.getByText("Peer Collaboration & Code Health")).toBeInTheDocument();
    expect(screen.getByText("Review Coverage")).toBeInTheDocument();
    expect(screen.getByText("Multi-Reviewer Rate")).toBeInTheDocument();
  });

  it("renders cross-repository delivery matrix", () => {
    renderWithProviders(<TeamInsightsPage />);

    expect(screen.getByText("Cross-Repository Delivery Matrix")).toBeInTheDocument();
    expect(screen.getByText("Macro Delivery Flow Timeline")).toBeInTheDocument();
  });
});
