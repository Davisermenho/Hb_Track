# HB_SCRIPT_KIND=FIX
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/fixes/db/fix_superadmin_pwd.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Corrigir senha do superadmin
"""
import bcrypt
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'))

# Gerar hash correto para Admin@123!
senha = "Admin@123!"
hash_correto = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print("\n" + "="*70)
print("CORREÇÃO DE SENHA DO SUPERADMIN")
print("="*70)
print(f"\nSenha: {senha}")
print(f"Novo hash: {hash_correto}\n")

# Conectar ao banco
url = os.getenv('DATABASE_URL_SYNC').replace('postgresql+psycopg2://', 'postgresql://').replace('postgresql+asyncpg://', 'postgresql://')
conn = psycopg2.connect(url)
cur = conn.cursor()

# Atualizar senha
cur.execute("""
    UPDATE users 
    SET password_hash = %s
    WHERE email = 'adm@handballtrack.app'
""", (hash_correto,))

conn.commit()

if cur.rowcount > 0:
    print("✅ Senha do superadmin atualizada com sucesso!")
    print("\nCREDENCIAIS:")
    print(f"   Email: adm@handballtrack.app")
    print(f"   Senha: {senha}")
    print("="*70 + "\n")
else:
    print("❌ Usuário não encontrado!")

cur.close()
conn.close()

