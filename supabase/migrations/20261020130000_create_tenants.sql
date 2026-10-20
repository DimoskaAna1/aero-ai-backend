-- Multi-industry tenant configuration read by GET /api/v1/tenant-config/{tenant_id}.
-- The API uses the service role key. Storefronts never query this table directly.

CREATE TABLE IF NOT EXISTS public.tenants (
  id text PRIMARY KEY,
  name text NOT NULL,
  industry text NOT NULL,
  agent_name text NOT NULL,
  greeting_message text NOT NULL,
  quick_chips jsonb NOT NULL DEFAULT '[]'::jsonb,
  system_prompt text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT tenants_id_not_blank CHECK (char_length(btrim(id)) > 0)
);

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.tenants FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.tenants TO service_role;

INSERT INTO public.tenants (
  id,
  name,
  industry,
  agent_name,
  greeting_message,
  quick_chips,
  system_prompt
)
VALUES
  (
    'demo-tenant',
    'Aero Lounge',
    'ecommerce',
    'Ana | Support Specialist',
    'Hey, I am Ana. How can I help?',
    '[
      {"label": "Free Shipping?", "message": "Is shipping free for this order?"},
      {"label": "Installment Plans", "message": "What installment plans can I use?"},
      {"label": "10% Discount", "message": "Can I get 10% off today?"}
    ]'::jsonb,
    'You are Ana, an e-commerce sales specialist for Aero Lounge. Help the shopper with products, shipping, installment plans, and checkout discounts. Stay concise and proactive.'
  ),
  (
    'care-clinic',
    'Northwind Clinic',
    'healthcare',
    'Ana | Care Coordinator',
    'Hello, I am Ana. I can help you book a visit or understand your care options.',
    '[
      {"label": "Book a visit", "message": "I would like to schedule an appointment."},
      {"label": "Office hours", "message": "What are your office hours?"},
      {"label": "Insurance", "message": "Which insurance plans do you accept?"}
    ]'::jsonb,
    'You are Ana, a healthcare care coordinator. Help the patient with appointments, office hours, and insurance questions. Do not diagnose. Stay calm and concise.'
  )
ON CONFLICT (id) DO NOTHING;

NOTIFY pgrst, 'reload schema';
