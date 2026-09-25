import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';
import Navbar from './components/Navbar';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import ScanNewPage from './pages/ScanNewPage';
import ScanResultPage from './pages/ScanResultPage';
import ConnectionsPage from './pages/ConnectionsPage';
import AgentSettingsPage from './pages/AgentSettingsPage';
import OtpVerificationPage from './pages/OtpVerificationPage';
import { SpeedInsights } from '@vercel/speed-insights/react';

/**
 * Auth-gated route wrapper.
 * Redirects to /auth if user is not authenticated.
 */
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingSpinner message="Authenticating..." />;
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  return children;
}

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner message="Authenticating..." />;
  }

  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
      <Route path="/auth" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <AuthPage />} />
      <Route path="/verify-otp" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <OtpVerificationPage />} />
      <Route path="/auth/verify" element={<Navigate to="/verify-otp" replace />} />
      <Route path="/auth/callback" element={<Navigate to="/dashboard" replace />} />

      {/* Protected */}
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/scan/new" element={<ProtectedRoute><ScanNewPage /></ProtectedRoute>} />
      <Route path="/scan/:id" element={<ProtectedRoute><ScanResultPage /></ProtectedRoute>} />
      <Route path="/connections" element={<ProtectedRoute><ConnectionsPage /></ProtectedRoute>} />
      <Route path="/settings/agent" element={<ProtectedRoute><AgentSettingsPage /></ProtectedRoute>} />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <ErrorBoundary>
          <main className="flex-1">
            <AppRoutes />
          </main>
        </ErrorBoundary>
        <SpeedInsights />
      </AuthProvider>
    </BrowserRouter>
  );
}
