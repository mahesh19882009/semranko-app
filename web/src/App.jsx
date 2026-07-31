import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicOnlyRoute from "./components/PublicOnlyRoute";
import PublicLayout from "./components/PublicLayout";
import AppLayout from "./components/AppLayout";

import HomePage from "./pages/HomePage";
import PricingPage from "./pages/PricingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import DashboardPage from "./pages/DashboardPage";
import ProjectsPage from "./pages/ProjectsPage";
import KeywordsPage from "./pages/KeywordsPage";
import KeywordResearchPage from "./pages/KeywordResearchPage";
import CompetitorsPage from "./pages/CompetitorsPage";
import KeywordListsPage from "./pages/KeywordListsPage";
import AIODashboardPage from "./pages/AIODashboardPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/pricing"
        element={
          <PublicLayout>
            <PricingPage />
          </PublicLayout>
        }
      />
      <Route
        path="/login"
        element={
          <PublicLayout>
            <LoginPage />
          </PublicLayout>
        }
      />
      <Route
        path="/register"
        element={
          <PublicLayout>
            <RegisterPage />
          </PublicLayout>
        }
      />
      <Route
        path="/verify-email"
        element={
          <PublicLayout>
            <VerifyEmailPage />
          </PublicLayout>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <PublicLayout>
            <ForgotPasswordPage />
          </PublicLayout>
        }
      />
      <Route
        path="/reset-password"
        element={
          <PublicLayout>
            <ResetPasswordPage />
          </PublicLayout>
        }
      />

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="keywords" element={<KeywordsPage />} />
        <Route path="keyword-research" element={<KeywordResearchPage />} />
        <Route path="competitors" element={<CompetitorsPage />} />
        <Route path="keyword-lists" element={<KeywordListsPage />} />
        <Route path="aio" element={<AIODashboardPage />} />
        <Route path="pricing" element={<PricingPage />} />
      </Route>

      <Route path="/dashboard" element={<Navigate to="/app" replace />} />
      <Route path="/projects" element={<Navigate to="/app/projects" replace />} />
      <Route path="/keywords" element={<Navigate to="/app/keywords" replace />} />
      <Route path="/competitors" element={<Navigate to="/app/competitors" replace />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
