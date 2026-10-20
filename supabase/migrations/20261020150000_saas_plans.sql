-- Publishable widget key, plan cap, bookings, and monthly usage.

ALTER TABLE public.tenants
  ADD COLUMN IF NOT EXISTS public_key text,
  ADD COLUMN IF NOT EXISTS plan text NOT NULL DEFAULT 'starter',
  ADD COLUMN IF NOT EXISTS monthly_message_limit integer NOT NULL DEFAULT 500;

CREATE TABLE IF NOT EXISTS public.tenant_bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  session_id text NOT NULL,
  when_text text NOT NULL,
  detail text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.tenant_usage (
  tenant_id text NOT NULL,
  month text NOT NULL,
  message_count integer NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, month)
);

ALTER TABLE public.tenant_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_usage ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.tenant_bookings FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.tenant_usage FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.tenant_bookings TO service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.tenant_usage TO service_role;
