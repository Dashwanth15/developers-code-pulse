import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";

// Pages
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { RepositoriesPage } from "@/pages/repositories/RepositoriesPage";
import { CommitsPage } from "@/pages/commits/CommitsPage";
import { PullRequestsPage } from "@/pages/pull-requests/PullRequestsPage";
import { ReviewsPage } from "@/pages/reviews/ReviewsPage";
import { TeamInsightsPage } from "@/pages/team-insights/TeamInsightsPage";
import { BottlenecksPage } from "@/pages/bottlenecks/BottlenecksPage";
import { DoraPage } from "@/pages/dora/DoraPage";
import { ReportsPage } from "@/pages/reports/ReportsPage";
import { IntegrationsPage } from "@/pages/integrations/IntegrationsPage";
import { SettingsPage } from "@/pages/settings/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="dcp-theme">
        <BrowserRouter>
          <Routes>
            <Route element={<DashboardLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/repositories" element={<RepositoriesPage />} />
              <Route path="/commits" element={<CommitsPage />} />
              <Route path="/pull-requests" element={<PullRequestsPage />} />
              <Route path="/reviews" element={<ReviewsPage />} />
              <Route path="/team-insights" element={<TeamInsightsPage />} />
              <Route path="/bottlenecks" element={<BottlenecksPage />} />
              <Route path="/dora" element={<DoraPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/integrations" element={<IntegrationsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
