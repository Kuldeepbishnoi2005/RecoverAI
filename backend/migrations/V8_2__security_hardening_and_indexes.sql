-- Phase 8B.1: Database Security Hardening and Query Indexing

-- 1. Explicitly pin search_path on all SECURITY DEFINER functions in public schema
ALTER FUNCTION public.get_auth_merchant_id() SET search_path = public;
ALTER FUNCTION public.handle_new_user() SET search_path = public;
ALTER FUNCTION public.rls_auto_enable() SET search_path = public;
ALTER FUNCTION public.seed_benchmark_data(jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb) SET search_path = public;

-- 2. Restrict direct RPC execution on SECURITY DEFINER administrative/trigger functions
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.seed_benchmark_data(jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_auth_merchant_id() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_auth_merchant_id() TO authenticated;

-- 3. Composite performance indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_audit_logs_merchant_created
  ON public.audit_logs(merchant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_merchant_created
  ON public.webhook_deliveries(merchant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recovery_actions_status_created
  ON public.recovery_actions(merchant_id, status, created_at DESC);
