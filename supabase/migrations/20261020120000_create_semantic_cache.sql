-- Semantic cache for tenant-scoped query reuse.
-- Run this in the Supabase SQL editor. The API must use the service role key:
-- the table is not readable or writable by the anon or authenticated roles.
--
-- Cosine similarity is 1 - (embedding <=> query). A hit requires similarity > 0.85.
-- embedding uses OpenAI text-embedding-3-small at 1536 dimensions.

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE TABLE public.semantic_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  session_id text,
  query_text text NOT NULL,
  response_text text NOT NULL,
  model text NOT NULL,
  embedding extensions.vector(1536) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT semantic_cache_tenant_id_not_blank CHECK (char_length(btrim(tenant_id)) > 0),
  CONSTRAINT semantic_cache_query_not_blank CHECK (char_length(query_text) > 0),
  CONSTRAINT semantic_cache_response_not_blank CHECK (char_length(response_text) > 0)
);

CREATE INDEX semantic_cache_embedding_hnsw_idx
  ON public.semantic_cache
  USING hnsw (embedding extensions.vector_cosine_ops);

CREATE INDEX semantic_cache_tenant_id_idx
  ON public.semantic_cache (tenant_id);

CREATE OR REPLACE FUNCTION public.match_semantic_cache(
  query_embedding extensions.vector(1536),
  match_tenant_id text,
  match_threshold double precision DEFAULT 0.85,
  match_count integer DEFAULT 1
)
RETURNS TABLE (
  id uuid,
  tenant_id text,
  query_text text,
  response_text text,
  model text,
  similarity double precision
)
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
BEGIN
  -- Keep scanning past other tenants so the nearest in-tenant row is not skipped.
  BEGIN
    PERFORM set_config('hnsw.iterative_scan', 'strict_order', true);
  EXCEPTION
    WHEN undefined_object THEN
      NULL;
  END;

  RETURN QUERY
  SELECT
    semantic_cache.id,
    semantic_cache.tenant_id,
    semantic_cache.query_text,
    semantic_cache.response_text,
    semantic_cache.model,
    1 - (semantic_cache.embedding <=> query_embedding) AS similarity
  FROM public.semantic_cache
  WHERE semantic_cache.tenant_id = match_tenant_id
    AND 1 - (semantic_cache.embedding <=> query_embedding) > match_threshold
  ORDER BY semantic_cache.embedding <=> query_embedding
  LIMIT LEAST(GREATEST(COALESCE(match_count, 1), 1), 5);
END;
$$;

ALTER TABLE public.semantic_cache ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.semantic_cache FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.semantic_cache TO service_role;

REVOKE ALL ON FUNCTION public.match_semantic_cache(extensions.vector, text, double precision, integer)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_semantic_cache(extensions.vector, text, double precision, integer)
  TO service_role;

NOTIFY pgrst, 'reload schema';
