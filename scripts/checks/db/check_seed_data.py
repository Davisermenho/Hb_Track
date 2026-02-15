# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/db/check_seed_data.py
# HB_SCRIPT_OUTPUTS=stdout
import psycopg2

conn = psycopg2.connect('postgresql://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev')
cur = conn.cursor()

print("=== VERIFICANDO DADOS E2E ===\n")

# Check treinador membership
cur.execute("""
    SELECT id, person_id, organization_id, role_id 
    FROM org_memberships 
    WHERE id = '88888888-8888-8888-8883-000000000003'
""")
result = cur.fetchone()
print(f"TREINADOR MEMBERSHIP: {result}")

# Check E2E org
cur.execute("""
    SELECT id, name 
    FROM organizations 
    WHERE id = '88888888-8888-8888-8888-000000000001'
""")
result = cur.fetchone()
print(f"E2E ORG: {result}\n")

# Check all E2E users
cur.execute("""
    SELECT u.email, om.id as membership_id, om.organization_id, r.code as role
    FROM users u
    JOIN persons p ON p.id = u.person_id
    JOIN org_memberships om ON om.person_id = p.id
    JOIN roles r ON r.id = om.role_id
    WHERE u.email LIKE 'e2e%'
    ORDER BY u.email
""")
results = cur.fetchall()
print("Todos usuários E2E:")
for r in results:
    print(f"  {r[0]:30} membership={r[1]} org={r[2]} role={r[3]}")

conn.close()

