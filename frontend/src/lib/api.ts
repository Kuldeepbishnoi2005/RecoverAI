import {
  Transaction,
  RevenueRiskEvent,
  RecoveryAction,
  AIDecision,
  AuditLog,
  OverviewMetrics
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchJson<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    throw new Error(`API Error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<{ status: string; timestamp: string }> {
    return fetchJson<{ status: string; timestamp: string }>('/health');
  },

  async getOverviewMetrics(): Promise<OverviewMetrics> {
    return fetchJson<OverviewMetrics>('/api/analytics/overview');
  },

  async getTransactions(): Promise<Transaction[]> {
    return fetchJson<Transaction[]>('/api/transactions');
  },

  async getRevenueRisk(): Promise<RevenueRiskEvent[]> {
    return fetchJson<RevenueRiskEvent[]>('/api/revenue-risk');
  },

  async getRevenueRiskDetail(id: string): Promise<RevenueRiskEvent> {
    return fetchJson<RevenueRiskEvent>(`/api/revenue-risk/${id}`);
  },

  async getRecoveryOpportunities(): Promise<RecoveryAction[]> {
    return fetchJson<RecoveryAction[]>('/api/recovery-opportunities');
  },

  async getAIDecisions(): Promise<AIDecision[]> {
    return fetchJson<AIDecision[]>('/api/ai-decisions');
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    return fetchJson<AuditLog[]>('/api/audit-logs');
  }
};
