-- =========================================================
-- MARAMARA - Migration 002: Profiles + role system
-- =========================================================

CREATE TYPE user_role AS ENUM ('user', 'therapist', 'admin');
CREATE TYPE link_status AS ENUM ('pending', 'active', 'revoked', 'rejected');

CREATE TABLE IF NOT EXISTS profiles (
    id                    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role                  user_role NOT NULL DEFAULT 'user',
    full_name             TEXT,
    email                 TEXT UNIQUE NOT NULL,
    avatar_url            TEXT,
    timezone              TEXT DEFAULT 'Asia/Jerusalem',
    language              TEXT DEFAULT 'he' CHECK (language IN ('he', 'en')),
    onboarding_completed  BOOLEAN NOT NULL DEFAULT FALSE,
    terms_accepted_at     TIMESTAMPTZ,
    privacy_accepted_at   TIMESTAMPTZ,
    deleted_at            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_role ON profiles(role);

CREATE TABLE IF NOT EXISTS therapist_patient_links (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    therapist_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    patient_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    status        link_status NOT NULL DEFAULT 'pending',
    invite_token  TEXT UNIQUE,
    invited_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at   TIMESTAMPTZ,
    revoked_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (therapist_id, patient_id)
);

CREATE INDEX idx_tpl_therapist ON therapist_patient_links(therapist_id);
CREATE INDEX idx_tpl_patient ON therapist_patient_links(patient_id);
CREATE INDEX idx_tpl_status ON therapist_patient_links(status);

-- Auto-create profile when auth user created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email)
    );
    RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
