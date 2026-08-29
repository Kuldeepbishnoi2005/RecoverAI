import {
  Transaction,
  RevenueRiskEvent,
  RecoveryOpportunity,
  AIDecision,
  AuditLog,
  OverviewMetrics,
  ManualReviewQueueItem,
  ApproveRequestPayload,
  RejectRequestPayload,
  WebhookDeliveryItem,
  DLQSummaryResponse
} from '../types';
import { supabase } from './supabase';

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? 'https://recoverai-6gwv.onrender.com'
    : 'http://localhost:8000');

async function getAuthHeader(): Promise<Record<string, string>> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      return { 'Authorization': `Bearer ${session.access_token}` };
    }
  } catch (e) {
    console.warn('Failed to retrieve Supabase auth session token:', e);
  }
  return {};
}

async function fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const authHeader = await getAuthHeader();
  const headers = {
    ...authHeader,
    ...(options.headers || {})
  };
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`API Error ${res.status}: ${res.statusText} ${errText}`);
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

  async getTransactions(status?: string, limit?: number): Promise<Transaction[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (limit) params.append('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
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
  },

  async getManualReviewQueue(): Promise<{ items: ManualReviewQueueItem[]; total: number }> {
    return fetchJson<{ items: ManualReviewQueueItem[]; total: number }>('/api/v1/manual-review/queue');
  },

  async getManualReviewDetail(actionId: string): Promise<any> {
    return fetchJson<any>(`/api/v1/manual-review/${actionId}`);
  },

  async approveManualReview(actionId: string, payload: ApproveRequestPayload): Promise<any> {
    const authHeader = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/v1/manual-review/${actionId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
        ...(payload.idempotency_key ? { 'X-Idempotency-Key': payload.idempotency_key } : {})
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Approval Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
  },

  async rejectManualReview(actionId: string, payload: RejectRequestPayload): Promise<any> {
    const authHeader = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/v1/manual-review/${actionId}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Rejection Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
  },

  manualReview: {
    async getQueue(): Promise<ManualReviewQueueItem[]> {
      const res = await fetchJson<{ items: ManualReviewQueueItem[]; total: number }>('/api/v1/manual-review/queue');
      return res.items || [];
    },
    async getActionDetails(actionId: string): Promise<any> {
      return fetchJson<any>(`/api/v1/manual-review/${actionId}`);
    },
    async approveAction(actionId: string, payload: ApproveRequestPayload, idempotencyKey?: string): Promise<any> {
      const key = idempotencyKey || payload.idempotency_key;
      const authHeader = await getAuthHeader();
      const res = await fetch(`${API_BASE}/api/v1/manual-review/${actionId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeader,
          ...(key ? { 'X-Idempotency-Key': key } : {})
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Approval Error ${res.status}: ${res.statusText}`);
      }
      return res.json();
    },
    async rejectAction(actionId: string, payload: RejectRequestPayload): Promise<any> {
      const authHeader = await getAuthHeader();
      const res = await fetch(`${API_BASE}/api/v1/manual-review/${actionId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeader
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Rejection Error ${res.status}: ${res.statusText}`);
      }
      return res.json();
    }
  },

  async getMerchantSettings(): Promise<any> {
    return fetchJson<any>('/api/v1/merchant-settings');
  },

  async updateMerchantSettings(payload: { autonomous_mode?: boolean; min_ai_confidence_threshold?: number; default_gateway?: string }): Promise<any> {
    const authHeader = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/v1/merchant-settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Update Settings Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
  },

  async rotateWebhookSecret(): Promise<{ success: boolean; new_webhook_secret: string; message: string }> {
    const authHeader = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/v1/merchant-settings/rotate-webhook-secret`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      }
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Rotate Secret Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
  },

  async getDLQActions(): Promise<{ items: any[]; total: number }> {
    return fetchJson<{ items: any[]; total: number }>('/api/v1/manual-review/dlq');
  },

  async replayAction(actionId: string, notes?: string): Promise<any> {
    const authHeader = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/v1/manual-review/${actionId}/replay`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      },
      body: JSON.stringify({ actor: 'merchant_admin', notes: notes || 'Manual action replay initiated' })
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Replay Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
  },

  async getWebhookLogs(limit: number = 20): Promise<{ items: any[]; total: number }> {
    return fetchJson<{ items: any[]; total: number }>(`/api/v1/merchant-settings/webhook-logs?limit=${limit}`);
  },

  async getWebhookDeliveries(limit: number = 20): Promise<{ items: WebhookDeliveryItem[]; total: number }> {
    return fetchJson<{ items: WebhookDeliveryItem[]; total: number }>(`/api/v1/webhook-deliveries?limit=${limit}`);
  },

  async getDLQSummary(): Promise<DLQSummaryResponse> {
    return fetchJson<DLQSummaryResponse>('/api/v1/manual-review/dlq-summary');
  }
};
