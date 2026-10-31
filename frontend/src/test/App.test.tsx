import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import App from "../App";

describe("Developers Code Pulse Frontend Shell", () => {
  it("renders the dashboard layout shell with title and tagline", () => {
    render(<App />);

    // Brand and header assertions
    expect(screen.getAllByText("Developers Code Pulse").length).toBeGreaterThan(0);
    expect(screen.getByText("Engineering Overview")).toBeInTheDocument();
    expect(
      screen.getByText("High-level metrics and workflow intelligence across your organization.")
    ).toBeInTheDocument();
  });

  it("renders core navigation items in sidebar", () => {
    render(<App />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Repositories")).toBeInTheDocument();
    expect(screen.getByText("Commit Analytics")).toBeInTheDocument();
    expect(screen.getByText("Pull Request Analytics")).toBeInTheDocument();
    expect(screen.getByText("Review Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Bottleneck Detection")).toBeInTheDocument();
    expect(screen.getByText("DORA Metrics")).toBeInTheDocument();
    expect(screen.getByText("Engineering Reports")).toBeInTheDocument();
    expect(screen.getByText("Integrations")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("navigates to Repositories page and renders empty state", async () => {
    const user = userEvent.setup();
    render(<App />);

    const repoLink = screen.getByText("Repositories");
    await user.click(repoLink);

    expect(screen.getByText("Connected Repositories")).toBeInTheDocument();
    expect(screen.getByText("No Repositories Connected Yet")).toBeInTheDocument();
  });

  it("navigates to Settings page and displays Anti-Surveillance commitment", async () => {
    const user = userEvent.setup();
    render(<App />);

    const settingsLink = screen.getByText("Settings");
    await user.click(settingsLink);

    expect(screen.getByText("Platform Settings & Governance")).toBeInTheDocument();
    expect(screen.getByText("Anti-Surveillance Commitment")).toBeInTheDocument();
    expect(
      screen.getByText(/No individual developer productivity scoring/i)
    ).toBeInTheDocument();
  });

  it("toggles visual theme button without error", async () => {
    const user = userEvent.setup();
    render(<App />);

    const themeButton = screen.getByRole("button", { name: /toggle visual theme/i });
    expect(themeButton).toBeInTheDocument();
    await user.click(themeButton);
  });
});
