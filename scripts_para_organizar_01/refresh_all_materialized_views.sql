-- ============================================================================
-- REFRESH ALL MATERIALIZED VIEWS - Sistema de Relatórios
-- ============================================================================
-- Refresha todas as 4 materialized views com CONCURRENTLY
-- (não bloqueia leituras - RF29, RD85)
--
-- Uso:
--   psql $DATABASE_URL -f backend/db/scripts/refresh_all_materialized_views.sql
--
-- Referências RAG: RF29 (performance), RD85 (índices), R21 (refresh)
-- ============================================================================

\timing on
\echo 'Iniciando refresh de todas as materialized views...'
\echo ''

-- ============================================================================
-- 1. mv_training_performance (R1)
-- ============================================================================
\echo '[1/4] Refreshing mv_training_performance...'
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_training_performance;
\echo '      ✓ mv_training_performance atualizada'
\echo ''

-- ============================================================================
-- 2. mv_athlete_training_summary (R2)
-- ============================================================================
\echo '[2/4] Refreshing mv_athlete_training_summary...'
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_athlete_training_summary;
\echo '      ✓ mv_athlete_training_summary atualizada'
\echo ''

-- ============================================================================
-- 3. mv_wellness_summary (R3)
-- ============================================================================
\echo '[3/4] Refreshing mv_wellness_summary...'
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_wellness_summary;
\echo '      ✓ mv_wellness_summary atualizada'
\echo ''

-- ============================================================================
-- 4. mv_medical_cases_summary (R4)
-- ============================================================================
\echo '[4/4] Refreshing mv_medical_cases_summary...'
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_medical_cases_summary;
\echo '      ✓ mv_medical_cases_summary atualizada'
\echo ''

-- ============================================================================
-- SUMMARY
-- ============================================================================
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo 'REFRESH COMPLETO - Todas as 4 materialized views foram atualizadas'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''
\echo 'Contagens atualizadas:'

SELECT 'mv_training_performance' AS view_name, COUNT(*) AS records FROM mv_training_performance
UNION ALL
SELECT 'mv_athlete_training_summary', COUNT(*) FROM mv_athlete_training_summary
UNION ALL
SELECT 'mv_wellness_summary', COUNT(*) FROM mv_wellness_summary
UNION ALL
SELECT 'mv_medical_cases_summary', COUNT(*) FROM mv_medical_cases_summary
ORDER BY view_name;

\echo ''
\echo 'Próximo refresh recomendado:'
\echo '  - mv_training_performance: A cada hora ou após treinos'
\echo '  - Demais views: Diário (1x ao dia)'
\echo ''
