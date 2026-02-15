-- ============================================================================
-- ÍNDICES PARA RELATÓRIOS E ALERTAS - HB Track
-- ============================================================================
-- Data: 2026-01-01
-- Objetivo: Acelerar queries de relatórios consolidados e alertas
-- Tabelas: attendance, training_sessions, match_attendance, wellness_post,
--          team_registrations, matches, athletes, medical_cases
-- ============================================================================

-- ============================================================================
-- ATTENDANCE (Assiduidade em treinos)
-- ============================================================================

-- Índice composto para relatórios de assiduidade por atleta
CREATE INDEX IF NOT EXISTS ix_attendance_athlete_session_active
ON attendance (athlete_id, training_session_id)
WHERE deleted_at IS NULL;

-- ============================================================================
-- TRAINING_SESSIONS (Sessões de treino)
-- ============================================================================

-- Índice composto team + data para relatórios por equipe
CREATE INDEX IF NOT EXISTS ix_training_sessions_team_date_active
ON training_sessions (team_id, session_at)
WHERE deleted_at IS NULL;

-- Índice composto team + season + data para filtros completos
CREATE INDEX IF NOT EXISTS ix_training_sessions_team_season_date
ON training_sessions (team_id, season_id, session_at)
WHERE deleted_at IS NULL;

-- ============================================================================
-- MATCH_ATTENDANCE (Presença em jogos)
-- ============================================================================

-- Índice composto para relatórios de minutos por atleta (só quem jogou)
CREATE INDEX IF NOT EXISTS ix_match_attendance_athlete_match_active
ON match_attendance (athlete_id, match_id)
WHERE deleted_at IS NULL AND played = true;

-- ============================================================================
-- WELLNESS_POST (Carga - RPE × minutos)
-- ============================================================================

-- Índice para queries de carga por atleta (cálculo de ACWR)
CREATE INDEX IF NOT EXISTS ix_wellness_post_athlete_session_active
ON wellness_post (athlete_id, training_session_id, created_at)
WHERE deleted_at IS NULL;

-- ============================================================================
-- TEAM_REGISTRATIONS (Vínculos ativos - joins frequentes)
-- ============================================================================

-- Índice parcial para vínculos ativos (usado em todos os relatórios)
CREATE INDEX IF NOT EXISTS ix_team_registrations_team_athlete_active
ON team_registrations (team_id, athlete_id)
WHERE end_at IS NULL AND deleted_at IS NULL;

-- ============================================================================
-- MATCHES (Jogos - relatórios de minutos)
-- ============================================================================

-- Índice para queries por temporada e data
CREATE INDEX IF NOT EXISTS ix_matches_season_date_active
ON matches (season_id, match_date)
WHERE deleted_at IS NULL;

-- ============================================================================
-- ATHLETES (Alertas de lesão)
-- ============================================================================

-- Índice parcial para atletas com flags médicas (alertas)
CREATE INDEX IF NOT EXISTS ix_athletes_medical_flags
ON athletes (organization_id)
WHERE deleted_at IS NULL 
  AND (injured = true OR medical_restriction = true OR load_restricted = true);

-- ============================================================================
-- MEDICAL_CASES (Casos médicos ativos)
-- ============================================================================

-- Índice para alertas de retorno de lesão
CREATE INDEX IF NOT EXISTS ix_medical_cases_athlete_status_active
ON medical_cases (athlete_id, status)
WHERE deleted_at IS NULL 
  AND status IN ('ativo', 'em_acompanhamento');

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

-- Listar índices criados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'ix_%_active' 
   OR indexname LIKE 'ix_%_date%'
   OR indexname LIKE 'ix_%_medical%'
ORDER BY tablename, indexname;
