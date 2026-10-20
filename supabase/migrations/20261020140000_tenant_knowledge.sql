-- Facts the agent is allowed to answer from. One row per product, policy, or FAQ.
-- Chat reads this table for the tenant in X-Tenant-Id. The bundled catalog in
-- app/services/knowledge.py is the same demo data used when the table is empty.

CREATE TABLE IF NOT EXISTS public.tenant_knowledge (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  kind text NOT NULL,
  title text NOT NULL,
  body text NOT NULL,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT tenant_knowledge_title_unique UNIQUE (tenant_id, title),
  CONSTRAINT tenant_knowledge_tenant_not_blank CHECK (char_length(btrim(tenant_id)) > 0)
);

CREATE INDEX IF NOT EXISTS tenant_knowledge_tenant_id_idx
  ON public.tenant_knowledge (tenant_id);

ALTER TABLE public.tenant_knowledge ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.tenant_knowledge FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.tenant_knowledge TO service_role;

INSERT INTO public.tenants (
  id, name, industry, agent_name, greeting_message, quick_chips, system_prompt
)
VALUES (
  'ananas',
  'Ananas',
  'ecommerce',
  'Ana | Shopping',
  'Zdravo, ja sam Ana. Mogu da nađem proizvod, cenu i rate.',
  '[
    {"label": "Veš mašina", "message": "Veš mašina"},
    {"label": "Na rate", "message": "Plaćanje na rate"},
    {"label": "Dostava", "message": "Dostava"}
  ]'::jsonb,
  'You are Ana, a shopping assistant for an Ananas-style marketplace. Answer only from the tenant catalog records. Prices are in MKD. Mention installments when the record includes them.'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.tenant_knowledge (tenant_id, kind, title, body, attributes)
VALUES
  (
    'health-clinic', 'faq', 'Radno vrijeme',
    'Naše radno vrijeme je od ponedjeljka do petka od 08:00 do 20:00h, te subotom od 08:00 do 14:00h.',
    '{}'::jsonb
  ),
  (
    'health-clinic', 'faq', 'Cjenovnik usluga',
    'Cijene osnovnih usluga: Opći pregled - 2.000 DEN, Specijalistički pregled - 3.500 DEN, Laboratorijske analize - od 1.200 DEN.',
    '{}'::jsonb
  ),
  (
    'health-clinic', 'faq', 'Zakaži pregled',
    'Za zakazivanje pregleda molimo navedite željeni datum, vrijeme i ime specijaliste.',
    '{}'::jsonb
  ),
  (
    'health-clinic', 'service', 'Specijalisti',
    'Dostupni specijalisti: Dr. Ana Petrov (opći pregled), Dr. Marko Iliev (specijalistički pregled).',
    '{"doctors": ["Dr. Ana Petrov", "Dr. Marko Iliev"]}'::jsonb
  ),
  (
    'ananas', 'policy', 'Dostava',
    'Besplatna dostava za porudžbine preko 3.000 MKD. Ispod tog iznosa dostava je 150 MKD. Isporuka stiže za 1 do 3 radna dana.',
    '{"free_over_mkd": 3000, "fee_mkd": 150}'::jsonb
  ),
  (
    'ananas', 'policy', 'Plaćanje na rate',
    'Plaćanje na 6 ili 12 rata bez kamate važi za proizvode skuplje od 6.000 MKD. Iznos rate piše uz svaki proizvod u katalogu.',
    '{}'::jsonb
  ),
  (
    'ananas', 'product', 'Samsung Galaxy A55 8/128',
    'Samsung Galaxy A55 8/128, telefoni. Cena 24.990 MKD. Na 12 rata po 2.083 MKD. Besplatna dostava.',
    '{"category": "Telefoni", "brand": "Samsung", "price_mkd": 24990, "installments": 12, "installment_mkd": 2083}'::jsonb
  ),
  (
    'ananas', 'product', 'iPhone 13 128GB',
    'iPhone 13 128GB, telefoni. Cena 42.990 MKD. Na 12 rata po 3.583 MKD. Besplatna dostava.',
    '{"category": "Telefoni", "brand": "Apple", "price_mkd": 42990, "installments": 12, "installment_mkd": 3583}'::jsonb
  ),
  (
    'ananas', 'product', 'Beko veš mašina 8 kg',
    'Beko veš mašina 8 kg, 1200 obrtaja, bela tehnika. Cena 27.990 MKD. Na 12 rata po 2.333 MKD. Besplatna dostava.',
    '{"category": "Bela tehnika", "brand": "Beko", "price_mkd": 27990, "installments": 12, "installment_mkd": 2333}'::jsonb
  ),
  (
    'ananas', 'product', 'Gorenje frižider NRK 619',
    'Gorenje kombinovani frižider NRK 619, bela tehnika. Cena 32.490 MKD. Na 12 rata po 2.708 MKD.',
    '{"category": "Bela tehnika", "brand": "Gorenje", "price_mkd": 32490, "installments": 12, "installment_mkd": 2708}'::jsonb
  ),
  (
    'ananas', 'product', 'Lenovo IdeaPad 3',
    'Lenovo IdeaPad 3, laptop 15.6 inča, 16 GB RAM. Cena 36.990 MKD. Na 12 rata po 3.083 MKD.',
    '{"category": "Laptopovi", "brand": "Lenovo", "price_mkd": 36990, "installments": 12, "installment_mkd": 3083}'::jsonb
  ),
  (
    'ananas', 'product', 'Xiaomi robot usisivač',
    'Xiaomi robot usisivač, mali kućni aparati. Cena 18.490 MKD. Na 6 rata po 3.082 MKD.',
    '{"category": "Mali kućni aparati", "brand": "Xiaomi", "price_mkd": 18490, "installments": 6, "installment_mkd": 3082}'::jsonb
  ),
  (
    'ananas', 'product', 'Philips sušilo za kosu',
    'Philips sušilo za kosu, lična nega. Cena 4.290 MKD. Jednokratno plaćanje, rate nisu dostupne ispod 6.000 MKD.',
    '{"category": "Lična nega", "brand": "Philips", "price_mkd": 4290, "installments": 0}'::jsonb
  ),
  (
    'ananas', 'product', 'Nike Revolution 7',
    'Nike Revolution 7, patike za trčanje. Cena 5.990 MKD. Jednokratno plaćanje.',
    '{"category": "Sport", "brand": "Nike", "price_mkd": 5990, "installments": 0}'::jsonb
  )
ON CONFLICT (tenant_id, title) DO NOTHING;

NOTIFY pgrst, 'reload schema';
