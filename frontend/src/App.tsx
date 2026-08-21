import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';
import { Overview } from './pages/Overview';
import { RevenueRisk } from './pages/RevenueRisk';
import { RecoveryOpportunities } from './pages/RecoveryOpportunities';
import { Transactions } from './pages/Transactions';
import { AIDecisions } from './pages/AIDecisions';
import { Analytics } from './pages/Analytics';
import { AuditLogs } from './pages/AuditLogs';
import { Settings } from './pages/Settings';
import { Help } from './pages/Help';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Overview />} />
          <Route path="overview" element={<Navigate to="/" replace />} />
          <Route path="revenue-risk" element={<RevenueRisk />} />
          <Route path="recovery-opportunities" element={<RecoveryOpportunities />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="ai-decisions" element={<AIDecisions />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="audit-logs" element={<AuditLogs />} />
          <Route path="settings" element={<Settings />} />
          <Route path="help" element={<Help />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
