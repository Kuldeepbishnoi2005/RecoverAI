import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { AppLayout } from './components/layouts/AppLayout';
import { PageLoadingFallback } from './components/common/PageLoadingFallback';

// Route-based code splitting using React.lazy
const Login = lazy(() => import('./pages/Login').then(m => ({ default: m.Login })));
const Overview = lazy(() => import('./pages/Overview').then(m => ({ default: m.Overview })));
const RevenueRisk = lazy(() => import('./pages/RevenueRisk').then(m => ({ default: m.RevenueRisk })));
const RecoveryOpportunities = lazy(() => import('./pages/RecoveryOpportunities').then(m => ({ default: m.RecoveryOpportunities })));
const Transactions = lazy(() => import('./pages/Transactions').then(m => ({ default: m.Transactions })));
const AIDecisions = lazy(() => import('./pages/AIDecisions').then(m => ({ default: m.AIDecisions })));
const Analytics = lazy(() => import('./pages/Analytics').then(m => ({ default: m.Analytics })));
const AuditLogs = lazy(() => import('./pages/AuditLogs').then(m => ({ default: m.AuditLogs })));
const ManualReview = lazy(() => import('./pages/ManualReview').then(m => ({ default: m.ManualReview })));
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const Help = lazy(() => import('./pages/Help').then(m => ({ default: m.Help })));

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoadingFallback />}>
          <Routes>
            {/* Public Unauthenticated Login Route */}
            <Route path="/login" element={<Login />} />

            {/* Authenticated Protected Dashboard Routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Overview />} />
                <Route path="overview" element={<Navigate to="/" replace />} />
                <Route path="revenue-risk" element={<RevenueRisk />} />
                <Route path="recovery-opportunities" element={<RecoveryOpportunities />} />
                <Route path="transactions" element={<Transactions />} />
                <Route path="ai-decisions" element={<AIDecisions />} />
                <Route path="manual-review" element={<ManualReview />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="audit-logs" element={<AuditLogs />} />
                <Route path="settings" element={<Settings />} />
                <Route path="help" element={<Help />} />
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
