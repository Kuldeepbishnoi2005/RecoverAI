-- Phase 8A Migration: Dynamic Merchant Settings, Webhook Logs, and Recovery DLQ State

-- 1. Create merchant_settings table
CREATE TABLE IF NOT EXISTS public.merchant_settings (
    merchant_id UUID PRIMARY KEY REFERENCES public.merchants(id) ON DELETE CASCADE,
    autonomous_mode BOOLEAN NOT NULL DEFAULT true,
    min_ai_confidence_threshold INTEGER NOT NULL DEFAULT 85 CHECK (min_ai_confidence_threshold >= 50 AND min_ai_confidence_threshold <= 99),
    webhook_secret TEXT NOT NULL,
    max_retry_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_retry_attempts >= 1 AND max_retry_attempts <= 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create webhook_deliveries table
CREATE TABLE IF NOT EXISTS public.webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES public.merchants(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    signature_verified BOOLEAN NOT NULL DEFAULT false,
    status_code INTEGER NOT NULL,
    payload JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Add DLQ and Replay tracking columns to recovery_actions table
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS is_dlq BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS replayed_at TIMESTAMPTZ;
ALTER TABLE public.recovery_actions ADD COLUMN IF NOT EXISTS replayed_by TEXT;

-- 4. Enable Row Level Security on new tables
ALTER TABLE public.merchant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_deliveries ENABLE ROW LEVEL SECURITY;

-- 5. Add RLS Policies for tenant isolation
DROP POLICY IF EXISTS merchant_settings_tenant_select ON public.merchant_settings;
CREATE POLICY merchant_settings_tenant_select ON public.merchant_settings
    FOR SELECT USING (merchant_id = public.get_auth_merchant_id());

DROP POLICY IF EXISTS merchant_settings_tenant_update ON public.merchant_settings;
CREATE POLICY merchant_settings_tenant_update ON public.merchant_settings
    FOR UPDATE USING (merchant_id = public.get_auth_merchant_id());

DROP POLICY IF EXISTS merchant_settings_tenant_insert ON public.merchant_settings;
CREATE POLICY merchant_settings_tenant_insert ON public.merchant_settings
    FOR INSERT WITH CHECK (merchant_id = public.get_auth_merchant_id());

DROP POLICY IF EXISTS webhook_deliveries_tenant_select ON public.webhook_deliveries;
CREATE POLICY webhook_deliveries_tenant_select ON public.webhook_deliveries
    FOR SELECT USING (merchant_id = public.get_auth_merchant_id());

DROP POLICY IF EXISTS webhook_deliveries_tenant_insert ON public.webhook_deliveries;
CREATE POLICY webhook_deliveries_tenant_insert ON public.webhook_deliveries
    FOR INSERT WITH CHECK (merchant_id = public.get_auth_merchant_id());

-- 6. Indexes for queries
CREATE INDEX IF NOT EXISTS idx_merchant_settings_updated_at ON public.merchant_settings(updated_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_merchant_event ON public.webhook_deliveries(merchant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recovery_actions_dlq ON public.recovery_actions(merchant_id, is_dlq, status);

-- 7. Seed default settings for existing merchants
INSERT INTO public.merchant_settings (merchant_id, autonomous_mode, min_ai_confidence_threshold, webhook_secret, max_retry_attempts)
SELECT id, true, 85, 'whsec_default_sandbox_secret_key_12345', 3
FROM public.merchants
ON CONFLICT (merchant_id) DO NOTHING;
