import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { AuthProvider } from "@/contexts/AuthContext";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { IntegrationsPage } from "@/pages/integrations/IntegrationsPage";

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

describe("Phase 2 Authentication & Integrations UI", () => {
  it("renders LoginPage with email, password, and submit button", () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByText("Sign in to your account")).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In/i })).toBeInTheDocument();
  });

  it("renders RegisterPage with full name, email, org name, and password", () => {
    renderWithProviders(<RegisterPage />);

    expect(screen.getByText("Create your account & team")).toBeInTheDocument();
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Work Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Organization \/ Team Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create Account & Get Started/i })).toBeInTheDocument();
  });

  it("renders IntegrationsPage with active GitHub connection and webhook configuration", async () => {
    renderWithProviders(<IntegrationsPage />);

    expect(screen.getByText("Platform Integrations")).toBeInTheDocument();
    expect(screen.getByText("GitHub Integration")).toBeInTheDocument();
    expect(screen.getByText(/Active • Dashwanth15/i)).toBeInTheDocument();
    expect(screen.getByText("Webhook Endpoint")).toBeInTheDocument();
    expect(screen.getByText("/api/v1/integrations/github/webhooks")).toBeInTheDocument();
  });
});
