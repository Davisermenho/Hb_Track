# HB_SCRIPT_KIND=SEED
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/seeds/official/seed_roles.py
# HB_SCRIPT_OUTPUTS=stdout
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://neondb_owner:npg_PrN5buzBWya1@ep-steep-bread-ad9uwqio-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require')
conn = engine.connect()

# Inserir roles básicas
roles = [
    ('MEMBRO', 'membro', 'Membro da organização'),
    ('ATLETA', 'atleta', 'Atleta'),
    ('TREINADOR', 'treinador', 'Treinador'),
    ('COORDENADOR', 'coordenador', 'Coordenador'),
    ('DIRIGENTE', 'dirigente', 'Dirigente'),
]

for code, name, desc in roles:
    conn.execute(text(f"INSERT INTO roles (code, name, description) VALUES ('{code}', '{name}', '{desc}') ON CONFLICT (code) DO NOTHING"))

conn.commit()
print('✅ Roles criadas com sucesso')

# Verificar
result = conn.execute(text("SELECT name FROM roles ORDER BY name")).fetchall()
print(f'📋 Roles no banco: {[r[0] for r in result]}')

