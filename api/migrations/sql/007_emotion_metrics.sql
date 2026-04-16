-- =========================================================
-- MARAMARA - Migration 007: Richer emotion + topic_mood columns
-- =========================================================

ALTER TABLE segment_analysis
  ADD COLUMN IF NOT EXISTS laugh_score REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS joy_score   REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS worry_score REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS anger_score REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS topic_mood  TEXT;  -- happy | worrying | annoying | neutral
