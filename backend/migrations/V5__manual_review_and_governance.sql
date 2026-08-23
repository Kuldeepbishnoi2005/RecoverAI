-- Phase 5 Migration: Recovery Execution & Manual Review
-- Migration file: backend/migrations/V5__manual_review_and_governance.sql

ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS override_strategy TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS policy_reason TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Index for enforcing unique idempotency key across non-null keys
CREATE UNIQUE INDEX IF NOT EXISTS idx_recovery_actions_idempotency_key ON public.recovery_actions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- Index for optimized manual review queue queries
CREATE INDEX IF NOT EXISTS idx_recovery_actions_manual_review ON public.recovery_actions(status, merchant_id, created_at DESC);
