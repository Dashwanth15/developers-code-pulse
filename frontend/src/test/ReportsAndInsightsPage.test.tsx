import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { ReportsPage } from "@/pages/reports/ReportsPage";
import { AiInsightsPage } from "@/pages/insights/AiInsightsPage";

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

describe("Phase 8 Engineering Reports UI", () => {
  it("renders page header, title, badges, and primary action buttons", () => {
    renderWithProviders(<ReportsPage />);

    expect(screen.getByRole("heading", { level: 1, name: /Engineering Reports/i })).toBeInTheDocument();
    expect(screen.getByText("PDF Engine & Insights")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate Report/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Schedule$/i })).toBeInTheDocument();
  });

  it("renders sub-navigation tabs for generated reports and automated schedules", () => {
    renderWithProviders(<ReportsPage />);

    expect(screen.getByRole("button", { name: /Generated Reports/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Automated Schedules/i })).toBeInTheDocument();
  });

  it("opens the Generate Report modal with all 5 report type options and AI toggle", async () => {
    renderWithProviders(<ReportsPage />);

    const generateBtn = screen.getByRole("button", { name: /Generate Report/i });
    fireEvent.click(generateBtn);

    expect(screen.getByText("Generate Engineering Report")).toBeInTheDocument();
    expect(screen.getAllByText(/Report Type/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Engineering Health Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Weekly Engineering Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Monthly Engineering Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Repository Health Report/i)).toBeInTheDocument();
    expect(screen.getByText(/DORA Metrics Report/i)).toBeInTheDocument();
    expect(screen.getByText(/Synthesize AI Insights & Executive Summary/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate & Render PDF/i })).toBeInTheDocument();

    // Close modal
    const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);
  });

  it("opens the Schedule Report modal with cadence options and recipient input", async () => {
    renderWithProviders(<ReportsPage />);

    const scheduleBtn = screen.getByRole("button", { name: /^Schedule$/i });
    fireEvent.click(scheduleBtn);

    expect(screen.getByText("Schedule Automated Report")).toBeInTheDocument();
    expect(screen.getByText(/Frequency/i)).toBeInTheDocument();
    expect(screen.getByText(/Timezone/i)).toBeInTheDocument();
    expect(screen.getByText(/Notification Recipients/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirm Schedule/i })).toBeInTheDocument();

    // Close modal
    const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);
  });
});

describe("Phase 8 AI Engineering Insights UI", () => {
  it("renders page header, title, and run AI synthesis action", () => {
    renderWithProviders(<AiInsightsPage />);

    expect(screen.getByRole("heading", { level: 1, name: /AI Engineering Insights/i })).toBeInTheDocument();
    expect(screen.getByText("Grounded Telemetry")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run AI Synthesis/i })).toBeInTheDocument();
  });

  it("renders AI provider status card and Anti-Surveillance assurance", () => {
    renderWithProviders(<AiInsightsPage />);

    expect(screen.getByText("AI Provider:")).toBeInTheDocument();
    expect(screen.getByText("Verified Grounded")).toBeInTheDocument();
    expect(screen.getByText("Anti-Surveillance & Grounding Manifesto Compliance")).toBeInTheDocument();
    expect(
      screen.getByText(/The system never generates individual developer velocity scores, rankings, or performance evaluations./i)
    ).toBeInTheDocument();
  });

  it("renders category and repository filter controls", () => {
    renderWithProviders(<AiInsightsPage />);

    expect(screen.getByText(/Filter Feed:/i)).toBeInTheDocument();
    expect(screen.getByText("All Insight Categories")).toBeInTheDocument();
    expect(screen.getByText("All Repositories")).toBeInTheDocument();
  });
});
