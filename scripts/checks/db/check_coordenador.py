# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/db/check_coordenador.py
# HB_SCRIPT_OUTPUTS=stdout
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Verificar equipe do coordenador
cur.execute("""
    SELECT 
        t.name,
        COUNT(DISTINCT a.id) as atletas,
        COUNT(DISTINCT tr.id) as trainings,
        COUNT(DISTINCT m.id) as matches
    FROM teams t
    LEFT JOIN team_registrations reg ON t.id = reg.team_id AND reg.deleted_at IS NULL
    LEFT JOIN athletes a ON reg.athlete_id = a.id AND a.deleted_at IS NULL
    LEFT JOIN training_sessions tr ON t.id = tr.team_id
    LEFT JOIN matches m ON t.id = m.our_team_id
    WHERE t.name = 'E2E-Equipe-Coordenador'
    GROUP BY t.id, t.name
""")

row = cur.fetchone()
if row:
    print("=" * 60)
    print(f"Equipe: {row[0]}")
    print(f"Atletas registrados: {row[1]}")
    print(f"Treinos: {row[2]}")
    print(f"Jogos: {row[3]}")
    print("=" * 60)
    
    # Detalhes dos treinos
    cur.execute("""
        SELECT main_objective, session_at::date, status
        FROM training_sessions
        WHERE team_id IN (SELECT id FROM teams WHERE name = 'E2E-Equipe-Coordenador')
        ORDER BY session_at
    """)
    print("\nTREINOS:")
    for training in cur.fetchall():
        print(f"  - {training[0]} | {training[1]} | {training[2]}")
    
    # Detalhes dos jogos
    cur.execute("""
        SELECT notes, match_date, status, final_score_home, final_score_away
        FROM matches
        WHERE our_team_id IN (SELECT id FROM teams WHERE name = 'E2E-Equipe-Coordenador')
        ORDER BY match_date
    """)
    print("\nJOGOS:")
    for match in cur.fetchall():
        score = f"{match[3]}-{match[4]}" if match[3] is not None else "Não finalizado"
        print(f"  - vs {match[0]} | {match[1]} | {match[2]} | {score}")
    
    # Detalhes dos atletas
    cur.execute("""
        SELECT a.athlete_name, a.shirt_number
        FROM athletes a
        JOIN team_registrations reg ON a.id = reg.athlete_id
        WHERE reg.team_id IN (SELECT id FROM teams WHERE name = 'E2E-Equipe-Coordenador')
          AND a.deleted_at IS NULL
          AND reg.deleted_at IS NULL
        ORDER BY a.shirt_number
    """)
    print("\nATLETAS:")
    for athlete in cur.fetchall():
        print(f"  - #{athlete[1]}: {athlete[0]}")
else:
    print("Equipe não encontrada!")

conn.close()

