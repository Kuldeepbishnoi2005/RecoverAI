import {
  Transaction,
  RevenueRiskEvent,
  RecoveryOpportunity,
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
    const raw = await fetchJson<any>('/api/v1/analytics/overview');
    const totalRisk = Number(raw.total_at_risk ?? raw.totalRiskAmount ?? raw.total_risk_amount ?? 0);
    const totalRecovered = Number(raw.total_recovered ?? raw.totalRecoveredAmount ?? raw.total_recovered_amount ?? 0);
    const activeRisk = Number(raw.active_risk_events ?? raw.activeRiskCount ?? raw.active_risk_count ?? 0);
    const aiDecisions = Number(raw.autonomous_actions_count ?? raw.aiDecisionsExecuted ?? raw.ai_decisions_executed ?? 0);
    const recRate = Number(raw.recovery_rate ?? raw.recoveryRate ?? 0);

    return {
      revenue_at_risk: totalRisk,
      potential_recovery: Number(raw.potential_recovery ?? 0),
      recovered_revenue: totalRecovered,
      recovery_rate: recRate,
      totalRiskAmount: totalRisk,
      totalRecoveredAmount: totalRecovered,
      activeRiskCount: activeRisk,
      aiDecisionsExecuted: aiDecisions,
      recoveryRate: recRate
    };
  },

  async getTransactions(merchantId?: string, limit?: number): Promise<Transaction[]> {
    let query = '';
    const params = new URLSearchParams();
    if (merchantId) params.append('merchant_id', merchantId);
    if (limit) params.append('limit', String(limit));
    if (params.toString()) query = `?${params.toString()}`;

    const rawList = await fetchJson<any[]>(`/api/v1/transactions${query}`);
    return rawList.map((t: any) => ({
      id: String(t.id),
      merchant_id: String(t.merchant_id || ''),
      customer_id: t.customer_id || 'cust_unknown',
      amount: Number(t.amount || 0),
      currency: t.currency || 'USD',
      status: t.status || 'succeeded',
      gateway: t.gateway || 'Razorpay',
      gateway_transaction_id: t.gateway_transaction_id || t.gateway_ref || '',
      risk_flag: Boolean(t.risk_flag),
      created_at: t.created_at || new Date().toISOString()
    }));
  },

  async getRevenueRisk(status?: string, severity?: string): Promise<RevenueRiskEvent[]> {
    const params = new URLSearchParams();
    if (status && status !== 'all') params.append('status', status);
    if (severity && severity !== 'all') params.append('severity', severity);
    const query = params.toString() ? `?${params.toString()}` : '';

    const rawList = await fetchJson<any[]>(`/api/v1/revenue-risk${query}`);
    return rawList.map((r: any) => ({
      id: String(r.id),
      merchant_id: String(r.merchant_id || ''),
      event_type: (r.event_type || r.risk_type || 'failed_payment') as any,
      customer_email: r.customer_email || r.details?.customer_email || `customer_${String(r.customer_id || r.id).slice(0, 6)}@merchant.com`,
      customer_id: r.customer_id || 'cust_unknown',
      amount: Number(r.amount ?? r.amount_at_risk ?? 0),
      currency: r.currency || 'USD',
      severity: (r.severity || 'medium') as any,
      risk_score: Number(r.risk_score ?? r.details?.risk_score ?? (r.severity === 'critical' ? 0.95 : r.severity === 'high' ? 0.85 : 0.65)),
      status: (r.status || 'open') as any,
      detected_at: r.detected_at || r.created_at || new Date().toISOString(),
      metadata: r.metadata || r.details || {}
    }));
  },

  async getRevenueRiskDetail(id: string): Promise<RevenueRiskEvent> {
    const r = await fetchJson<any>(`/api/v1/revenue-risk/${id}`);
    return {
      id: String(r.id),
      merchant_id: String(r.merchant_id || ''),
      event_type: (r.event_type || r.risk_type || 'failed_payment') as any,
      customer_email: r.customer_email || r.details?.customer_email || `customer_${String(r.customer_id || r.id).slice(0, 6)}@merchant.com`,
      customer_id: r.customer_id || 'cust_unknown',
      amount: Number(r.amount ?? r.amount_at_risk ?? 0),
      currency: r.currency || 'USD',
      severity: (r.severity || 'medium') as any,
      risk_score: Number(r.risk_score ?? r.details?.risk_score ?? (r.severity === 'critical' ? 0.95 : r.severity === 'high' ? 0.85 : 0.65)),
      status: (r.status || 'open') as any,
      detected_at: r.detected_at || r.created_at || new Date().toISOString(),
      metadata: r.metadata || r.details || {}
    };
  },

  async getRecoveryOpportunities(): Promise<RecoveryOpportunity[]> {
    const rawList = await fetchJson<any[]>('/api/v1/recovery-opportunities');
    return rawList.map((a: any) => ({
      id: String(a.id),
      title: a.title || (a.action_type ? a.action_type.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) : 'Autonomous Retry Protocol'),
      description: a.description || a.parameters?.description || 'Smart payment retry window & localized dunning sequence.',
      potential_revenue: Number(a.potential_revenue ?? a.parameters?.expected_recovery_amount ?? a.parameters?.amount ?? 12500),
      success_rate: Number(a.success_rate ?? a.parameters?.estimated_success_rate ?? 78),
      risk_type: a.risk_type || a.action_type || 'failed_payment',
      recommended_action: a.recommended_action || 'Execute Workflow',
      status: a.status || 'pending'
    }));
  },

  async getAIDecisions(): Promise<AIDecision[]> {
    const rawList = await fetchJson<any[]>('/api/v1/ai-decisions');
    return rawList.map((d: any) => ({
      id: String(d.id),
      merchant_id: String(d.merchant_id || ''),
      risk_event_id: d.risk_event_id || 'evt_unknown',
      model_name: d.model_name || 'gemini-3-flash-preview',
      action_type: d.action_type || d.recommended_strategy || 'smart_retry_schedule',
      confidence_score: Number(d.confidence_score ?? 0.92),
      reasoning: d.reasoning || d.root_cause_analysis || 'Autonomous decision executed based on merchant payment parameters.',
      payload: d.payload || d.reasoning_raw || {},
      status: (d.status || 'executed') as any,
      executed_at: d.executed_at || d.created_at,
      created_at: d.created_at || new Date().toISOString()
    }));
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const rawList = await fetchJson<any[]>('/api/v1/audit-logs');
    return rawList.map((a: any) => ({
      id: String(a.id),
      merchant_id: String(a.merchant_id || ''),
      actor_type: a.actor_type || 'system',
      actor_id: a.actor_id || null,
      action: a.action || 'RLS_POLICY_EVAL',
      entity_type: a.entity_type || 'system',
      entity_id: a.entity_id || null,
      changes: a.changes || {},
      created_at: a.created_at || new Date().toISOString(),
      user: a.user || a.actor_id || a.actor_type || 'system_rls',
      ip: a.ip || a.changes?.ip || a.entity_type || 'internal',
      status: a.status || a.changes?.status || 'SUCCESS',
      timestamp: a.timestamp || a.created_at || new Date().toISOString()
    }));
  }
};

