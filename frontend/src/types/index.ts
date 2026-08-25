export type RiskSeverity = 'low' | 'medium' | 'high' | 'critical';
export type RiskStatus = 'detected' | 'analyzing' | 'action_recommended' | 'action_executed' | 'recovered' | 'lost' | 'dismissed' | 'open' | 'in_recovery' | 'resolved';
export type TransactionStatus = 'succeeded' | 'failed' | 'pending' | 'disputed';
export type ActionType = 'smart_retry' | 'dunning_email' | 'chargeback_defense' | 'discount_offer' | 'smart_retry_schedule' | 'personalized_dunning' | 'chargeback_prevention_offer';
export type ActionStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled' | 'executed' | 'pending_approval';
export type ActorType = 'system' | 'ai_agent' | 'user';

export interface Merchant {
  id: string;
  name: string;
  slug: string | null;
  plan: string;
  currency: string;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Profile {
  id: string;
  merchant_id: string | null;
  full_name: string | null;
  email: string | null;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  merchant_id: string;
  external_customer_id: string | null;
  name: string | null;
  email: string | null;
  phone: string | null;
  risk_score: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  merchant_id: string;
  customer_id: string | null;
  external_transaction_id?: string | null;
  amount: number;
  currency: string;
  status: TransactionStatus;
  gateway: string;
  payment_gateway?: string;
  gateway_transaction_id?: string;
  error_code?: string;
  error_message?: string;
  risk_flag?: boolean;
  payment_method?: string | null;
  failure_reason?: string | null;
  failure_code?: string | null;
  metadata?: Record<string, any>;
  occurred_at?: string;
  created_at: string;
  customer?: Customer;
}

export interface PaymentAttempt {
  id: string;
  transaction_id: string;
  merchant_id: string;
  gateway: string;
  attempt_number: number;
  status: string;
  error_code: string | null;
  error_description: string | null;
  raw_response: Record<string, any>;
  created_at: string;
}

export interface RevenueRiskEvent {
  id: string;
  merchant_id: string;
  transaction_id?: string | null;
  customer_id?: string | null;
  customer_email: string;
  event_type: string;
  risk_type?: string;
  severity: RiskSeverity;
  amount: number;
  amount_at_risk?: number;
  currency?: string;
  risk_score: number;
  status: RiskStatus;
  detected_at: string;
  updated_at?: string;
  metadata?: Record<string, any>;
  details?: Record<string, any>;
  created_at?: string;
  transaction?: Transaction;
  customer?: Customer;
}

export interface AIDecision {
  id: string;
  merchant_id: string;
  risk_event_id: string | null;
  model_name?: string;
  action_type: string;
  confidence_score: number;
  reasoning: string;
  payload: Record<string, any>;
  status: ActionStatus;
  executed_at?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  root_cause_analysis?: string | null;
  recommended_strategy?: string | null;
  reasoning_raw?: Record<string, any>;
  created_at: string;
  risk_event?: RevenueRiskEvent;
}

export interface RecoveryOpportunity {
  id: string;
  title: string;
  description: string;
  potential_revenue: number;
  success_rate: number;
  risk_type: string;
  recommended_action: string;
  status: string;
}

export interface RecoveryAction {
  id: string;
  merchant_id: string;
  risk_event_id: string | null;
  ai_decision_id: string | null;
  action_type: ActionType;
  status: ActionStatus;
  parameters: Record<string, any>;
  scheduled_at: string | null;
  executed_at: string | null;
  created_at: string;
  risk_event?: RevenueRiskEvent;
  ai_decision?: AIDecision;
}

export interface RecoveryResult {
  id: string;
  merchant_id: string;
  recovery_action_id: string;
  recovered_amount: number;
  is_successful: boolean;
  result_details: Record<string, any>;
  measured_at: string;
  created_at: string;
  recovery_action?: RecoveryAction;
}

export interface AuditLog {
  id: string;
  merchant_id?: string;
  actor_type?: ActorType;
  actor_id?: string | null;
  action: string;
  entity_type?: string;
  entity_id?: string | null;
  changes?: Record<string, any>;
  created_at?: string;
  user?: string;
  ip?: string;
  status?: string;
  timestamp?: string;
}

export interface EvaluationRun {
  id: string;
  merchant_id: string | null;
  name: string;
  status: string;
  metrics: Record<string, any>;
  completed_at: string | null;
  created_at: string;
}

export interface OverviewMetrics {
  revenue_at_risk?: number;
  potential_recovery?: number;
  recovered_revenue?: number;
  recovery_rate?: number;
  totalRiskAmount: number;
  totalRecoveredAmount: number;
  activeRiskCount: number;
  aiDecisionsExecuted: number;
  recoveryRate: number;
}

export interface ManualReviewQueueItem {
  id: string;
  action_id: string;
  transaction_id: string;
  merchant_id: string;
  strategy: string;
  action_type?: string;
  status: ActionStatus | string;
  attempted_amount: number;
  amount?: number;
  currency?: string;
  risk_score: number;
  policy_reason: string;
  reason?: string;
  execution_strategy?: string;
  policy_check_results?: { reason?: string };
  created_at: string;
  transaction?: Transaction;
}

export interface ManualReviewActionDetail {
  action: ManualReviewQueueItem;
  transaction?: Transaction;
  ai_decision?: AIDecision;
}

export interface ApproveRequestPayload {
  override_strategy?: string;
  actor?: string;
  approver_id?: string;
  approver_role?: string;
  notes?: string;
  idempotency_key?: string;
}

export interface RejectRequestPayload {
  rejection_reason: string;
  actor?: string;
  rejected_by?: string;
  approver_role?: string;
}

export interface MerchantSettings {
  id: string;
  merchant_id: string;
  autonomous_mode: boolean;
  min_ai_confidence_threshold: number;
  default_gateway: string;
  webhook_secret_masked: string;
  created_at?: string;
  updated_at?: string;
}

export interface DLQActionItem extends ManualReviewQueueItem {
  retry_count: number;
  last_error: string;
  is_dlq: boolean;
}
