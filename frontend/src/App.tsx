import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Login } from './pages/Login';
import { AppLayout } from './components/layouts/AppLayout';
import { Overview } from './pages/Overview';
import { RevenueRisk } from './pages/RevenueRisk';
import { RecoveryOpportunities } from './pages/RecoveryOpportunities';
import { Transactions } from './pages/Transactions';
import { AIDecisions } from './pages/AIDecisions';
import { Analytics } from './pages/Analytics';
import { AuditLogs } from './pages/AuditLogs';
import { ManualReview } from './pages/ManualReview';
import { Settings } from './pages/Settings';
import { Help } from './pages/Help';

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
