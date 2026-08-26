-- Migration V8_1: Add default_gateway column to merchant_settings
ALTER TABLE public.merchant_settings
ADD COLUMN IF NOT EXISTS default_gateway TEXT NOT NULL DEFAULT 'sandbox'
CHECK (default_gateway IN ('sandbox', 'stripe', 'razorpay'));
