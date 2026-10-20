-- Tenant keys, plans, usage, and bookings are read and written by the API.
-- data/store.json is no longer a source of truth.

GRANT SELECT, INSERT, UPDATE ON TABLE public.tenants TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tenant_knowledge TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tenant_bookings TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tenant_usage TO service_role;

UPDATE public.tenants
SET public_key = 'pk_ananas_demo', plan = 'demo', monthly_message_limit = 10000
WHERE id = 'ananas' AND (public_key IS NULL OR btrim(public_key) = '');

UPDATE public.tenants
SET public_key = 'pk_demo_tenant', plan = 'demo', monthly_message_limit = 10000
WHERE id = 'demo-tenant' AND (public_key IS NULL OR btrim(public_key) = '');

INSERT INTO public.tenants (
  id, name, industry, agent_name, greeting_message, quick_chips, system_prompt,
  public_key, plan, monthly_message_limit
)
VALUES (
  'health-clinic',
  'Health Clinic',
  'healthcare',
  'Ana | Care Coordinator',
  'Zdravo, kako mozam da pomognam?',
  '[]'::jsonb,
  'Answer only from this clinic''s stored facts. Do not diagnose or invent prices.',
  'pk_health_demo',
  'demo',
  10000
)
ON CONFLICT (id) DO UPDATE
SET public_key = COALESCE(NULLIF(btrim(public.tenants.public_key), ''), EXCLUDED.public_key);

CREATE OR REPLACE FUNCTION public.consume_tenant_message(p_tenant text, p_month text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_plan text;
  v_limit integer;
  v_used integer;
BEGIN
  IF p_tenant IS NULL OR btrim(p_tenant) = '' OR p_month IS NULL OR btrim(p_month) = '' THEN
    RAISE EXCEPTION 'tenant and month are required';
  END IF;

  SELECT plan, monthly_message_limit
    INTO v_plan, v_limit
  FROM public.tenants
  WHERE id = p_tenant;

  IF NOT FOUND THEN
    v_plan := 'starter';
    v_limit := 500;
  END IF;

  INSERT INTO public.tenant_usage (tenant_id, month, message_count)
  VALUES (p_tenant, p_month, 1)
  ON CONFLICT (tenant_id, month)
  DO UPDATE SET message_count = public.tenant_usage.message_count + 1
  WHERE public.tenant_usage.message_count < v_limit
  RETURNING message_count INTO v_used;

  IF v_used IS NULL THEN
    SELECT message_count INTO v_used
    FROM public.tenant_usage
    WHERE tenant_id = p_tenant AND month = p_month;
    RETURN jsonb_build_object(
      'allowed', false,
      'used', COALESCE(v_used, v_limit),
      'limit', v_limit,
      'plan', v_plan
    );
  END IF;

  RETURN jsonb_build_object('allowed', true, 'used', v_used, 'limit', v_limit, 'plan', v_plan);
END;
$$;

REVOKE ALL ON FUNCTION public.consume_tenant_message(text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.consume_tenant_message(text, text) TO service_role;

NOTIFY pgrst, 'reload schema';
