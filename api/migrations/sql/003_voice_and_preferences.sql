-- =========================================================
-- MARAMARA - Migration 003: Voice profiles + recording preferences
-- =========================================================

-- Voice enrollment: 192-dim embedding (ECAPA-TDNN SpeechBrain)
CREATE TABLE IF NOT EXISTS voice_profiles (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    embedding_vector      vector(192),
    sample_duration_sec   REAL NOT NULL,
    model_version         TEXT NOT NULL DEFAULT 'speechbrain/spkrec-ecapa-voxceleb',
    confidence_baseline   REAL,
    sample_count          INT NOT NULL DEFAULT 3,
    enrolled_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retrained_count       INT NOT NULL DEFAULT 0
);

-- Approximate nearest-neighbour index for speaker verification
CREATE INDEX idx_voice_embedding
  ON voice_profiles USING hnsw (embedding_vector vector_cosine_ops);

CREATE TRIGGER trg_voice_profiles_updated_at
    BEFORE UPDATE ON voice_profiles
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();


CREATE TABLE IF NOT EXISTS recording_preferences (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    start_hour        SMALLINT NOT NULL DEFAULT 8 CHECK (start_hour BETWEEN 0 AND 23),
    end_hour          SMALLINT NOT NULL DEFAULT 22 CHECK (end_hour BETWEEN 0 AND 23),
    auto_off_night    BOOLEAN NOT NULL DEFAULT TRUE,
    sleep_start       SMALLINT DEFAULT 23,
    sleep_end         SMALLINT DEFAULT 7,
    pause_until       TIMESTAMPTZ,
    sensitivity_level SMALLINT NOT NULL DEFAULT 3 CHECK (sensitivity_level BETWEEN 1 AND 5),
    excluded_ranges   JSONB DEFAULT '[]'::JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_recording_prefs_updated_at
    BEFORE UPDATE ON recording_preferences
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
