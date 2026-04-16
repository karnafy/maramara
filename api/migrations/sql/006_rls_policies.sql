-- =========================================================
-- MARAMARA - Migration 006: Row Level Security policies
-- =========================================================

-- Enable RLS on all user-owned tables
ALTER TABLE profiles                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapist_patient_links  ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_profiles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE recording_preferences    ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_segments           ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts              ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_analysis         ENABLE ROW LEVEL SECURITY;
ALTER TABLE detected_terms           ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_metrics            ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_metrics           ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapist_notes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_flags               ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapist_access_log     ENABLE ROW LEVEL SECURITY;


-- Helper: is caller an admin?
CREATE OR REPLACE FUNCTION public.is_admin() RETURNS BOOLEAN
LANGUAGE SQL STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$;

-- Helper: is caller a therapist?
CREATE OR REPLACE FUNCTION public.is_therapist() RETURNS BOOLEAN
LANGUAGE SQL STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles
    WHERE id = auth.uid() AND role = 'therapist'
  );
$$;

-- Helper: is target_user linked to caller (who must be therapist)?
CREATE OR REPLACE FUNCTION public.is_my_patient(target_user UUID) RETURNS BOOLEAN
LANGUAGE SQL STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM therapist_patient_links
    WHERE therapist_id = auth.uid()
      AND patient_id = target_user
      AND status = 'active'
  );
$$;


-- ============================================================
-- profiles
-- ============================================================
CREATE POLICY "profiles_read_self"
  ON profiles FOR SELECT
  USING (id = auth.uid());

CREATE POLICY "profiles_read_linked_patient"
  ON profiles FOR SELECT
  USING (is_my_patient(id));

CREATE POLICY "profiles_read_admin"
  ON profiles FOR SELECT
  USING (is_admin());

CREATE POLICY "profiles_update_self"
  ON profiles FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

CREATE POLICY "profiles_admin_all"
  ON profiles FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());


-- ============================================================
-- therapist_patient_links
-- ============================================================
CREATE POLICY "tpl_read_involved"
  ON therapist_patient_links FOR SELECT
  USING (therapist_id = auth.uid() OR patient_id = auth.uid() OR is_admin());

CREATE POLICY "tpl_insert_therapist"
  ON therapist_patient_links FOR INSERT
  WITH CHECK (is_therapist() AND therapist_id = auth.uid());

CREATE POLICY "tpl_update_involved"
  ON therapist_patient_links FOR UPDATE
  USING (therapist_id = auth.uid() OR patient_id = auth.uid() OR is_admin());


-- ============================================================
-- Owner-only pattern for sensitive tables
-- ============================================================

-- voice_profiles: only owner (therapist cannot see raw embedding)
CREATE POLICY "voice_owner" ON voice_profiles FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- recording_preferences: only owner
CREATE POLICY "prefs_owner" ON recording_preferences FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());


-- ============================================================
-- audio_segments: owner + linked therapist (read-only) + admin
-- ============================================================
CREATE POLICY "segments_owner" ON audio_segments FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY "segments_read_therapist" ON audio_segments FOR SELECT
  USING (is_my_patient(user_id));

CREATE POLICY "segments_admin" ON audio_segments FOR SELECT
  USING (is_admin());


-- ============================================================
-- transcripts / segment_analysis / detected_terms
-- owner + linked therapist (read-only) + admin
-- ============================================================
CREATE POLICY "transcripts_owner" ON transcripts FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "transcripts_therapist_read" ON transcripts FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "transcripts_admin" ON transcripts FOR SELECT USING (is_admin());

CREATE POLICY "analysis_owner" ON segment_analysis FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "analysis_therapist_read" ON segment_analysis FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "analysis_admin" ON segment_analysis FOR SELECT USING (is_admin());

CREATE POLICY "terms_owner" ON detected_terms FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "terms_therapist_read" ON detected_terms FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "terms_admin" ON detected_terms FOR SELECT USING (is_admin());


-- ============================================================
-- daily / weekly metrics
-- ============================================================
CREATE POLICY "daily_owner" ON daily_metrics FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "daily_therapist_read" ON daily_metrics FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "daily_admin" ON daily_metrics FOR SELECT USING (is_admin());

CREATE POLICY "weekly_owner" ON weekly_metrics FOR ALL
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "weekly_therapist_read" ON weekly_metrics FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "weekly_admin" ON weekly_metrics FOR SELECT USING (is_admin());


-- ============================================================
-- therapist_notes: therapist owns, patient can read own
-- ============================================================
CREATE POLICY "notes_therapist_all" ON therapist_notes FOR ALL
  USING (therapist_id = auth.uid()) WITH CHECK (therapist_id = auth.uid());

CREATE POLICY "notes_patient_read" ON therapist_notes FOR SELECT
  USING (patient_id = auth.uid());

CREATE POLICY "notes_admin" ON therapist_notes FOR SELECT USING (is_admin());


-- ============================================================
-- risk_flags: owner + linked therapist + admin (write)
-- ============================================================
CREATE POLICY "risk_owner_read" ON risk_flags FOR SELECT
  USING (user_id = auth.uid());
CREATE POLICY "risk_therapist_read" ON risk_flags FOR SELECT
  USING (is_my_patient(user_id));
CREATE POLICY "risk_admin" ON risk_flags FOR ALL
  USING (is_admin()) WITH CHECK (is_admin());


-- ============================================================
-- therapist_access_log: append-only, readable by involved + admin
-- ============================================================
CREATE POLICY "access_log_read_self" ON therapist_access_log FOR SELECT
  USING (therapist_id = auth.uid() OR patient_id = auth.uid() OR is_admin());
