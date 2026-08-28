-- Migration V9: Encrypted Multi-Tenant Gateway Credentials
-- Secure, isolated envelope encryption storage for tenant payment secrets.

-- 1. Create merchant_credentials table
CREATE TABLE IF NOT EXISTS public.merchant_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES public.merchants(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('stripe', 'razorpay', 'webhook')),
    credential_type TEXT NOT NULL CHECK (credential_type IN ('secret_key', 'key_id', 'key_secret', 'webhook_secret')),
    encrypted_payload TEXT NOT NULL,  -- Base64 AES-256-GCM ciphertext + tag encrypted under random DEK
    wrapped_dek TEXT NOT NULL,        -- Base64 AES-256-GCM wrapped DEK encrypted under versioned KEK
    payload_nonce TEXT NOT NULL,      -- Base64 12-byte nonce for payload encryption
    wrapped_dek_nonce TEXT NOT NULL,  -- Base64 12-byte nonce for DEK wrapping
    key_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_merchant_provider_credential UNIQUE (merchant_id, provider, credential_type)
);

-- 2. Enable Row Level Security (RLS)
ALTER TABLE public.merchant_credentials ENABLE ROW LEVEL SECURITY;

-- 3. Security Policies:
-- Revoke all direct public / authenticated role permissions
REVOKE ALL ON TABLE public.merchant_credentials FROM public, anon, authenticated;

-- Allow ALL operations only for trusted backend service_role
DROP POLICY IF EXISTS merchant_credentials_service_role_all ON public.merchant_credentials;
CREATE POLICY merchant_credentials_service_role_all ON public.merchant_credentials
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 4. Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_merchant_credentials_lookup
    ON public.merchant_credentials (merchant_id, provider);

CREATE INDEX IF NOT EXISTS idx_merchant_credentials_updated
    ON public.merchant_credentials (updated_at DESC);
