# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/db/check_coord_train.py
# HB_SCRIPT_OUTPUTS=stdout
import psycopg2

conn = psycopg2.connect('postgresql://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev')
cur = conn.cursor()

print("=== VERIFICANDO CONTEXTO COORDENADOR vs TREINADOR ===\n")

# Coordenador
cur.execute("""
    SELECT om.id, om.organization_id, u.email, r.code
    FROM org_memberships om
    JOIN users u ON u.person_id = om.person_id
    JOIN roles r ON r.id = om.role_id
    WHERE u.email = 'e2e.coordenador@teste.com'
""")
coord = cur.fetchone()
print(f"COORDENADOR: membership={coord[0]}, org={coord[1]}, email={coord[2]}, role={coord[3]}")

# Treinador
cur.execute("""
    SELECT om.id, om.organization_id, u.email, r.code
    FROM org_memberships om
    JOIN users u ON u.person_id = om.person_id
    JOIN roles r ON r.id = om.role_id
    WHERE u.email = 'e2e.treinador@teste.com'
""")
train = cur.fetchone()
print(f"TREINADOR:   membership={train[0]}, org={train[1]}, email={train[2]}, role={train[3]}\n")

if coord[1] == train[1]:
    print("✅ Mesma organização!")
else:
    print(f"❌ Organizações diferentes! Coordenador={coord[1]}, Treinador={train[1]}")

conn.close()

