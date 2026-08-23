-- Phase 6: Enable Row Level Security (RLS) and Tenant Isolation across all tables

-- Enable RLS on all 11 application tables
ALTER TABLE public.merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revenue_risk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recovery_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recovery_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_decisions ENABLE ROW LEVEL SECURITY;

-- Helper function to resolve auth user's merchant_id
CREATE OR REPLACE FUNCTION public.get_auth_merchant_id()
RETURNS uuid
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT merchant_id FROM public.profiles WHERE id = auth.uid() LIMIT 1;
$$;

-- Trigger to automatically create a profile for new auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  default_merchant UUID;
BEGIN
  SELECT id INTO default_merchant FROM public.merchants ORDER BY created_at ASC LIMIT 1;
  INSERT INTO public.profiles (id, merchant_id, full_name, email, role)
  VALUES (
    NEW.id,
    COALESCE(
      CASE WHEN (NEW.raw_user_meta_data->>'merchant_id') IS NOT NULL AND (NEW.raw_user_meta_data->>'merchant_id') != ''
           THEN (NEW.raw_user_meta_data->>'merchant_id')::uuid ELSE NULL END,
      default_merchant
    ),
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'role', 'admin')
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    merchant_id = COALESCE(profiles.merchant_id, EXCLUDED.merchant_id);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Merchants Policies
DROP POLICY IF EXISTS merchants_tenant_select ON public.merchants;
CREATE POLICY merchants_tenant_select ON public.merchants
    FOR SELECT USING (id = public.get_auth_merchant_id());

DROP POLICY IF EXISTS merchants_tenant_update ON public.merchants;
CREATE POLICY merchants_tenant_update ON public.merchants
    FOR UPDATE USING (id = public.get_auth_merchant_id());

-- Profiles Policies
DROP POLICY IF EXISTS profiles_self_select ON public.profiles;
CREATE POLICY profiles_self_select ON public.profiles
    FOR SELECT USING (id = auth.uid());

DROP POLICY IF EXISTS profiles_self_update ON public.profiles;
CREATE POLICY profiles_self_update ON public.profiles
    FOR UPDATE USING (id = auth.uid());

-- Customers Policies
DROP POLICY IF EXISTS customers_tenant_all ON public.customers;
CREATE POLICY customers_tenant_all ON public.customers
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Transactions Policies
DROP POLICY IF EXISTS transactions_tenant_all ON public.transactions;
CREATE POLICY transactions_tenant_all ON public.transactions
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Payment Attempts Policies
DROP POLICY IF EXISTS payment_attempts_tenant_all ON public.payment_attempts;
CREATE POLICY payment_attempts_tenant_all ON public.payment_attempts
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Revenue Risk Events Policies
DROP POLICY IF EXISTS revenue_risk_events_tenant_all ON public.revenue_risk_events;
CREATE POLICY revenue_risk_events_tenant_all ON public.revenue_risk_events
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Evaluation Runs Policies
DROP POLICY IF EXISTS evaluation_runs_tenant_all ON public.evaluation_runs;
CREATE POLICY evaluation_runs_tenant_all ON public.evaluation_runs
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Recovery Results Policies
DROP POLICY IF EXISTS recovery_results_tenant_all ON public.recovery_results;
CREATE POLICY recovery_results_tenant_all ON public.recovery_results
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Audit Logs Policies
DROP POLICY IF EXISTS audit_logs_tenant_all ON public.audit_logs;
CREATE POLICY audit_logs_tenant_all ON public.audit_logs
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Recovery Actions Policies
DROP POLICY IF EXISTS recovery_actions_tenant_all ON public.recovery_actions;
CREATE POLICY recovery_actions_tenant_all ON public.recovery_actions
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- AI Decisions Policies
DROP POLICY IF EXISTS ai_decisions_tenant_all ON public.ai_decisions;
CREATE POLICY ai_decisions_tenant_all ON public.ai_decisions
    FOR ALL USING (merchant_id = public.get_auth_merchant_id());

-- Ensure Indexes exist for performance
CREATE INDEX IF NOT EXISTS idx_customers_merchant_id ON public.customers(merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_id ON public.transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_payment_attempts_merchant_id ON public.payment_attempts(merchant_id);
CREATE INDEX IF NOT EXISTS idx_revenue_risk_events_merchant_id ON public.revenue_risk_events(merchant_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_merchant_id ON public.evaluation_runs(merchant_id);
CREATE INDEX IF NOT EXISTS idx_recovery_results_merchant_id ON public.recovery_results(merchant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_merchant_id ON public.audit_logs(merchant_id);
CREATE INDEX IF NOT EXISTS idx_recovery_actions_merchant_id ON public.recovery_actions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_merchant_id ON public.ai_decisions(merchant_id);
