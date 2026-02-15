# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/run/run_validate_implementation.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Script de validação da implementação Steps 1-3 do Training Module
"""
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv('DATABASE_URL')
# Trocar asyncpg por psycopg2 para execução síncrona
if DATABASE_URL and DATABASE_URL.startswith('postgresql+asyncpg'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg', 'postgresql+psycopg2')
engine = create_engine(DATABASE_URL)

print("\n" + "=" * 80)
print(" VALIDAÇÃO DA IMPLEMENTAÇÃO - STEPS 1-3")
print("=" * 80)

# 1. VALIDAR TRIGGERS
print("\n### 1. TRIGGERS CRIADOS ###\n")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            trigger_name, 
            event_manipulation, 
            event_object_table,
            action_timing
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public' 
        AND trigger_name LIKE 'tr_%'
        ORDER BY event_object_table, trigger_name
    """))
    triggers = result.fetchall()
    
    if triggers:
        for t in triggers:
            print(f"✓ {t[0]:50} {t[3]:7} {t[1]:10} on {t[2]}")
        print(f"\n Total: {len(triggers)} triggers")
    else:
        print("❌ Nenhum trigger encontrado!")

# 2. VALIDAR NOVAS TABELAS (Step 3)
print("\n### 2. TABELAS CRIADAS (Step 3) ###\n")
expected_tables = [
    'wellness_reminders',
    'athlete_badges',
    'team_wellness_rankings',
    'training_alerts',
    'training_suggestions',
    'exercises',
    'exercise_tags',
    'exercise_favorites',
    'training_analytics_cache',
    'data_access_logs',
    'export_jobs',
    'export_rate_limits',
    'data_retention_logs'
]

with engine.connect() as conn:
    for table in expected_tables:
        result = conn.execute(text(f"""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = '{table}'
        """))
        exists = result.scalar() > 0
        status = "✓" if exists else "❌"
        print(f"{status} {table}")

# 3. VALIDAR ÍNDICES
print("\n### 3. ÍNDICES CRIADOS ###\n")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            schemaname, 
            tablename, 
            indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN (
            'wellness_reminders', 'athlete_badges', 'team_wellness_rankings',
            'training_alerts', 'training_suggestions', 'exercises',
            'exercise_tags', 'exercise_favorites', 'training_analytics_cache',
            'data_access_logs', 'export_jobs', 'export_rate_limits', 
            'data_retention_logs', 'training_sessions', 'wellness_pre', 'wellness_post'
        )
        AND indexname NOT LIKE '%_pkey'
        ORDER BY tablename, indexname
    """))
    indexes = result.fetchall()
    
    if indexes:
        current_table = None
        for idx in indexes:
            if current_table != idx[1]:
                current_table = idx[1]
                print(f"\n{current_table}:")
            print(f"  ✓ {idx[2]}")
        print(f"\nTotal: {len(indexes)} índices")
    else:
        print("❌ Nenhum índice encontrado!")

# 4. VALIDAR COLUNAS ADICIONADAS (Step 2)
print("\n### 4. COLUNAS ADICIONADAS (Step 2) ###\n")
columns_to_check = [
    ('teams', 'alert_threshold_multiplier'),
    ('wellness_pre', 'locked_at'),
    ('wellness_post', 'locked_at')
]

with engine.connect() as conn:
    for table, column in columns_to_check:
        result = conn.execute(text(f"""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = '{table}' 
            AND column_name = '{column}'
        """))
        exists = result.scalar() > 0
        status = "✓" if exists else "❌"
        print(f"{status} {table}.{column}")

# 5. TESTAR TRIGGER DE INTERNAL_LOAD
print("\n### 5. TESTE DO TRIGGER fn_calculate_internal_load ###\n")
with engine.connect() as conn:
    try:
        # Verificar se existe wellness_post com dados
        result = conn.execute(text("""
            SELECT id, minutes_effective, session_rpe, internal_load 
            FROM wellness_post 
            WHERE minutes_effective IS NOT NULL 
            AND session_rpe IS NOT NULL
            LIMIT 3
        """))
        posts = result.fetchall()
        
        if posts:
            print("Validando cálculo automático de internal_load:\n")
            for post in posts:
                expected_load = post[1] * post[2] if post[1] and post[2] else None
                actual_load = post[3]
                match = expected_load == actual_load
                status = "✓" if match else "❌"
                print(f"{status} ID {post[0]}: {post[1]} min × RPE {post[2]} = {actual_load} (esperado: {expected_load})")
        else:
            print("⚠️  Nenhum wellness_post com dados para validar")
    except Exception as e:
        print(f"❌ Erro ao testar trigger: {e}")

print("\n" + "=" * 80)
print(" FIM DA VALIDAÇÃO")
print("=" * 80 + "\n")

