-- =========================================================
-- MARAMARA - Migration 008: Relational uplift/downlift metrics
-- =========================================================
-- Adds 4 new analysis dimensions that capture the emotional
-- give-and-take between the speaker and others, beyond the
-- existing self_criticism_score:
--
--   self_compliment_score    — speaker lifting themselves up
--   compliment_others_score  — speaker lifting others up
--   external_positive_score  — speaker reports being lifted by others
--   external_negative_score  — speaker reports being brought down by others
--
-- Each score is 0.0..1.0, per-segment, produced by the
-- Claude analysis prompt (services/analysis.py).

ALTER TABLE segment_analysis
  ADD COLUMN IF NOT EXISTS self_compliment_score    NUMERIC(3,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS compliment_others_score  NUMERIC(3,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS external_positive_score  NUMERIC(3,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS external_negative_score  NUMERIC(3,2) DEFAULT 0;

COMMENT ON COLUMN segment_analysis.self_compliment_score IS
  '0-1: speaker giving themselves positive recognition ("I did well", "I am proud of myself")';
COMMENT ON COLUMN segment_analysis.compliment_others_score IS
  '0-1: speaker giving others positive recognition or praise';
COMMENT ON COLUMN segment_analysis.external_positive_score IS
  '0-1: speaker recounts being lifted / validated / praised by others';
COMMENT ON COLUMN segment_analysis.external_negative_score IS
  '0-1: speaker recounts being criticized / dismissed / brought down by others';
