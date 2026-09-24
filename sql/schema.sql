-- ==============================================================================
-- Nexus Database Schema — Supabase PostgreSQL
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- 
-- Prerequisites:
--   1. Create a Supabase project at https://supabase.com/dashboard
--   2. Enable Email auth in Authentication → Providers
--   3. (Optional) Enable Google OAuth in Authentication → Providers
--   4. Run this entire file in the SQL Editor
-- ==============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: connections
-- Stores OAuth integrations for external providers (Gmail, Slack, etc.)
-- Encrypted tokens are stored server-side via Fernet (never exposed to client)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,                       -- 'gmail', 'slack', 'outlook'
    encrypted_tokens TEXT NOT NULL,               -- Fernet-encrypted OAuth credentials
    status TEXT NOT NULL DEFAULT 'active',         -- 'active', 'revoked', 'error'
    metadata JSONB DEFAULT '{}'::jsonb,           -- provider-specific info (email, scopes)
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connections_user_id ON public.connections(user_id);
CREATE INDEX IF NOT EXISTS idx_connections_provider ON public.connections(provider);

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: agent_profiles
-- Customizable LLM agent profiles for Layer 4 explanations
-- user_id = NULL → global default available to all users
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.agent_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_profiles_user_id ON public.agent_profiles(user_id);

-- Seed the global default agent profile
INSERT INTO public.agent_profiles (id, user_id, name, system_prompt, is_default)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    NULL,
    'Standard Security Analyst (Default)',
    'You are Nexus AI, an elite cybersecurity incident responder and threat analyst. You receive ONLY verified, structured JSON evidence extracted by deterministic detection rules. You NEVER hallucinate indicators not in the evidence bundle. Provide concise, clear, plain-English explanations of the attack vectors, evaluate risk objectively, and formulate actionable SOAR containment artifacts when severity is high.',
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: scans
-- Master record for every submitted phishing analysis
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,                      -- 'email', 'url', 'qr', 'screenshot'
    raw_input_ref TEXT,                             -- preview snippet or storage reference
    risk_score INTEGER NOT NULL DEFAULT 0           -- 0–100
        CONSTRAINT chk_risk_score CHECK (risk_score >= 0 AND risk_score <= 100),
    severity TEXT NOT NULL DEFAULT 'LOW'            -- 'LOW', 'MEDIUM', 'HIGH'
        CONSTRAINT chk_severity CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    status TEXT NOT NULL DEFAULT 'processing'       -- 'queued', 'processing', 'completed', 'failed'
        CONSTRAINT chk_status CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    recommended_action TEXT,
    explanation TEXT,
    agent_profile_id UUID REFERENCES public.agent_profiles(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_user_id ON public.scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON public.scans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_severity ON public.scans(severity);
CREATE INDEX IF NOT EXISTS idx_scans_status ON public.scans(status);

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: evidence
-- Individual findings from Layer 1 (deterministic) & Layer 2 (behavioral NLP)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES public.scans(id) ON DELETE CASCADE,
    layer INTEGER NOT NULL                          -- 1 = deterministic, 2 = behavioral
        CONSTRAINT chk_layer CHECK (layer IN (1, 2)),
    type TEXT NOT NULL,                             -- e.g. 'typosquatting', 'urgency', 'fear'
    severity TEXT NOT NULL                          -- 'LOW', 'MEDIUM', 'HIGH'
        CONSTRAINT chk_ev_severity CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    human_label TEXT NOT NULL,                      -- Plain-English description
    raw_match TEXT NOT NULL,                        -- The matched domain/token/expression
    span_start INTEGER,                             -- Start offset in original text
    span_end INTEGER,                               -- End offset in original text
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_scan_id ON public.evidence(scan_id);
CREATE INDEX IF NOT EXISTS idx_evidence_layer ON public.evidence(layer);

-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: reports
-- SOAR containment artifacts generated for HIGH-risk scans (Layer 4)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES public.scans(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL                        -- 'cert', 'dns_sinkhole', 'suricata'
        CONSTRAINT chk_report_type CHECK (report_type IN ('cert', 'dns_sinkhole', 'suricata')),
    content TEXT NOT NULL,
    submitted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_scan_id ON public.reports(scan_id);
CREATE INDEX IF NOT EXISTS idx_reports_type ON public.reports(report_type);


-- ═══════════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS) POLICIES
-- All tables are protected — users can only access their own data.
-- The backend uses the Supabase SERVICE ROLE KEY which bypasses RLS.
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE public.connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

-- ── Connections ──────────────────────────────────────────────────────────────
CREATE POLICY "connections_user_all" ON public.connections
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ── Agent Profiles ──────────────────────────────────────────────────────────
CREATE POLICY "agent_profiles_select" ON public.agent_profiles
    FOR SELECT TO authenticated
    USING (user_id IS NULL OR auth.uid() = user_id);

CREATE POLICY "agent_profiles_insert" ON public.agent_profiles
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "agent_profiles_update" ON public.agent_profiles
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "agent_profiles_delete" ON public.agent_profiles
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- ── Scans ────────────────────────────────────────────────────────────────────
CREATE POLICY "scans_user_all" ON public.scans
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ── Evidence (read-only via scan ownership) ──────────────────────────────────
CREATE POLICY "evidence_select" ON public.evidence
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.scans
        WHERE scans.id = evidence.scan_id AND scans.user_id = auth.uid()
    ));

CREATE POLICY "evidence_insert" ON public.evidence
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.scans
        WHERE scans.id = evidence.scan_id AND scans.user_id = auth.uid()
    ));

-- ── Reports (read-only via scan ownership) ───────────────────────────────────
CREATE POLICY "reports_select" ON public.reports
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.scans
        WHERE scans.id = reports.scan_id AND scans.user_id = auth.uid()
    ));

CREATE POLICY "reports_insert" ON public.reports
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.scans
        WHERE scans.id = reports.scan_id AND scans.user_id = auth.uid()
    ));


-- ═══════════════════════════════════════════════════════════════════════════════
-- HELPER FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Auto-update the updated_at timestamp on row changes
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
CREATE TRIGGER set_updated_at_connections
    BEFORE UPDATE ON public.connections
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_agent_profiles
    BEFORE UPDATE ON public.agent_profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_scans
    BEFORE UPDATE ON public.scans
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
