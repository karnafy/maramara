-- =========================================================
-- MARAMARA - Migration 005: Daily/weekly metrics + therapist notes + risk flags
-- =========================================================

CREATE TABLE IF NOT EXISTS daily_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    positive_count      INT NOT NULL DEFAULT 0,
    negative_count      INT NOT NULL DEFAULT 0,
    curse_count         INT NOT NULL DEFAULT 0,
    complaint_count     INT NOT NULL DEFAULT 0,
    calming_count       INT NOT NULL DEFAULT 0,
    self_criticism_count INT NOT NULL DEFAULT 0,
    polarity_score      REAL NOT NULL DEFAULT 0,
    intensity_avg       REAL NOT NULL DEFAULT 0,
    peak_frustration_hour SMALLINT,
    top_trigger_topic   TEXT,
    top_calming_topic   TEXT,
    summary_text        TEXT,
    total_segments      INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, date)
);

CREATE INDEX idx_daily_user_date ON daily_metrics(user_id, date DESC);

CREATE TRIGGER trg_daily_metrics_updated_at
    BEFORE UPDATE ON daily_metrics
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();


CREATE TABLE IF NOT EXISTS weekly_metrics (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    week_start            DATE NOT NULL,
    negativity_avg        REAL NOT NULL DEFAULT 0,
    positivity_avg        REAL NOT NULL DEFAULT 0,
    curse_delta           REAL,
    improvement_score     REAL,
    top_trigger_topics    JSONB DEFAULT '[]'::JSONB,
    top_calming_topics    JSONB DEFAULT '[]'::JSONB,
    top_phrases           JSONB DEFAULT '[]'::JSONB,
    therapist_summary     TEXT,
    crewai_insights       JSONB DEFAULT '{}'::JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, week_start)
);

CREATE INDEX idx_weekly_user_week ON weekly_metrics(user_id, week_start DESC);

CREATE TRIGGER trg_weekly_metrics_updated_at
    BEFORE UPDATE ON weekly_metrics
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();


CREATE TABLE IF NOT EXISTS therapist_notes (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    therapist_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    patient_id   UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    note_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    title        TEXT,
    body         TEXT NOT NULL,
    tags         JSONB DEFAULT '[]'::JSONB,
    is_intervention_marker BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notes_therapist_patient ON therapist_notes(therapist_id, patient_id, note_date DESC);

CREATE TRIGGER trg_notes_updated_at
    BEFORE UPDATE ON therapist_notes
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();


CREATE TYPE risk_severity AS ENUM ('info', 'low', 'medium', 'high', 'critical');
CREATE TYPE risk_status   AS ENUM ('open', 'reviewing', 'resolved', 'dismissed');

CREATE TABLE IF NOT EXISTS risk_flags (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    audio_segment_id  UUID REFERENCES audio_segments(id) ON DELETE SET NULL,
    risk_type         TEXT NOT NULL,
    severity          risk_severity NOT NULL DEFAULT 'medium',
    status            risk_status NOT NULL DEFAULT 'open',
    description       TEXT,
    handled_by        UUID REFERENCES profiles(id),
    handled_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_user_status ON risk_flags(user_id, status) WHERE status = 'open';
CREATE INDEX idx_risk_severity ON risk_flags(severity, created_at DESC) WHERE status = 'open';


-- Audit log for therapist access (compliance / GDPR)
CREATE TABLE IF NOT EXISTS therapist_access_log (
    id           BIGSERIAL PRIMARY KEY,
    therapist_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    patient_id   UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    action       TEXT NOT NULL,
    resource     TEXT,
    ip_address   INET,
    user_agent   TEXT,
    accessed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_access_therapist_time ON therapist_access_log(therapist_id, accessed_at DESC);
CREATE INDEX idx_access_patient_time ON therapist_access_log(patient_id, accessed_at DESC);
