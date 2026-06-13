-- Enable the moddatetime extension so our updated_at triggers work
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

-- Table: users
CREATE TABLE public.users (
  id              UUID          PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email           TEXT          NOT NULL UNIQUE,
  full_name       TEXT,
  avatar_url      TEXT,
  auth_provider   TEXT          NOT NULL DEFAULT 'email',   -- 'email' | 'google'
  plan            TEXT          NOT NULL DEFAULT 'free',    -- 'free' | 'pro'
  timezone        TEXT          NOT NULL DEFAULT 'Asia/Colombo',
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_plan  ON public.users(plan);

-- Trigger to auto-update updated_at for users
CREATE TRIGGER set_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

-- Table: documents
CREATE TABLE public.documents (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  document_type   TEXT          NOT NULL,   -- 'invoice' | 'quotation' | 'proposal' | 'receipt' | 'purchase_order'
  document_number TEXT,                      -- e.g. 'INV-001'
  client_name     TEXT,
  template_id     TEXT          NOT NULL,
  accent_color    TEXT          NOT NULL DEFAULT '#2563EB',
  status          TEXT          NOT NULL DEFAULT 'draft',  -- 'draft' | 'exported'
  exported_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_user_id       ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type          ON public.documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status        ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at    ON public.documents(created_at DESC);

-- Trigger to auto-update updated_at for documents
CREATE TRIGGER set_documents_updated_at
  BEFORE UPDATE ON public.documents
  FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

-- Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_self ON public.users
  FOR ALL
  USING (id = auth.uid());

CREATE POLICY documents_self ON public.documents
  FOR ALL
  USING (user_id = auth.uid());
