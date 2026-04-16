-- =========================================================
-- MARAMARA - Migration 004: Audio segments + transcripts + analysis
-- =========================================================

CREATE TYPE transcript_status  AS ENUM ('pending', 'processing', 'completed', 'failed', 'skipped');
CREATE TYPE analysis_status    AS ENUM ('pending', 'processing', 'completed', 'failed', 'skipped');
CREATE TYPE polarity_type      AS ENUM ('positive', 'neutral', 'negative', 'mixed');
CREATE TYPE term_type          AS ENUM ('positive', 'negative', 'curse', 'trigger', 'calming', 'gratitude', 'self_criticism', 'absolutist');


CREATE TABLE IF NOT EXISTS audio_segments (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    started_at           TIMESTAMPTZ NOT NULL,
    ended_at             TIMESTAMPTZ NOT NULL,
    duration_sec         REAL NOT NULL,
    speech_detected      BOOLEAN NOT NULL DEFAULT FALSE,
    speaker_match_score  REAL,
    matched_to_user      BOOLEAN NOT NULL DEFAULT FALSE,
    transcript_status    transcript_status NOT NULL DEFAULT 'pending',
    analysis_status      analysis_status NOT NULL DEFAULT 'pending',
    raw_audio_path       TEXT,
    client_meta          JSONB DEFAULT '{}'::JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at           TIMESTAMPTZ
);

CREATE INDEX idx_segments_user_time ON audio_segments(user_id, started_at DESC);
CREATE INDEX idx_segments_status ON audio_segments(analysis_status) WHERE analysis_status != 'completed';


CREATE TABLE IF NOT EXISTS transcripts (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_segment_id  UUID NOT NULL UNIQUE REFERENCES audio_segments(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    transcript_text   TEXT NOT NULL,
    language          TEXT NOT NULL DEFAULT 'he',
    word_count        INT NOT NULL DEFAULT 0,
    confidence        REAL,
    model_used        TEXT DEFAULT 'faster-whisper-large-v3',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transcripts_user ON transcripts(user_id, created_at DESC);
CREATE INDEX idx_transcripts_text_trgm ON transcripts USING gin (transcript_text gin_trgm_ops);


CREATE TABLE IF NOT EXISTS segment_analysis (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_segment_id     UUID NOT NULL UNIQUE REFERENCES audio_segments(id) ON DELETE CASCADE,
    user_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    polarity             polarity_type NOT NULL,
    intensity_score      REAL NOT NULL CHECK (intensity_score BETWEEN 0 AND 10),
    complaint_score      REAL DEFAULT 0,
    curse_score          REAL DEFAULT 0,
    calming_score        REAL DEFAULT 0,
    self_talk_score      REAL DEFAULT 0,
    self_criticism_score REAL DEFAULT 0,
    absolutism_score     REAL DEFAULT 0,
    blame_score          REAL DEFAULT 0,
    primary_topic        TEXT,
    secondary_topic      TEXT,
    trigger_detected     BOOLEAN DEFAULT FALSE,
    trigger_description  TEXT,
    calming_detected     BOOLEAN DEFAULT FALSE,
    calming_description  TEXT,
    cognitive_patterns   JSONB DEFAULT '[]'::JSONB,
    tags                 JSONB DEFAULT '[]'::JSONB,
    llm_model_used       TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_user_time ON segment_analysis(user_id, created_at DESC);
CREATE INDEX idx_analysis_polarity ON segment_analysis(user_id, polarity);
CREATE INDEX idx_analysis_topic ON segment_analysis(user_id, primary_topic);


CREATE TABLE IF NOT EXISTS detected_terms (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    audio_segment_id UUID REFERENCES audio_segments(id) ON DELETE CASCADE,
    term             TEXT NOT NULL,
    term_type        term_type NOT NULL,
    count            INT NOT NULL DEFAULT 1,
    language         TEXT DEFAULT 'he',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_terms_user_type ON detected_terms(user_id, term_type);
CREATE INDEX idx_terms_term_trgm ON detected_terms USING gin (term gin_trgm_ops);
