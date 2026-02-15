# HB_SCRIPT_KIND=FIX
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/fixes/db/fix_validate_hash.py
# HB_SCRIPT_OUTPUTS=stdout
import bcrypt
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'))

# Conectar ao banco
url = os.getenv('DATABASE_URL_SYNC').replace('postgresql+psycopg2://', 'postgresql://').replace('postgresql+asyncpg://', 'postgresql://')
conn = psycopg2.connect(url)
cur = conn.cursor()

# Buscar hash do banco
cur.execute("SELECT password_hash FROM users WHERE email = 'adm@handballtrack.app'")
result = cur.fetchone()

if result:
    hash_banco = result[0]
    senha = "Admin@123!"
    
    print("\n" + "="*70)
    print("VALIDAÇÃO DE SENHA")
    print("="*70)
    print(f"\nEmail: adm@handballtrack.app")
    print(f"Senha: {senha}")
    print(f"Hash no banco: {hash_banco}")
    
    # Testar senha
    valido = bcrypt.checkpw(senha.encode('utf-8'), hash_banco.encode('utf-8'))
    
    if valido:
        print("\n✅ SENHA VÁLIDA! O hash está correto.")
    else:
        print("\n❌ SENHA INVÁLIDA! O hash NÃO corresponde à senha.")
        print("\nGerando hash correto...")
        novo_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        print(f"Novo hash: {novo_hash}")
        
        # Atualizar no banco
        cur.execute("UPDATE users SET password_hash = %s WHERE email = 'adm@handballtrack.app'", (novo_hash,))
        conn.commit()
        print("\n✅ Hash atualizado no banco!")
    
    print("="*70 + "\n")
else:
    print("❌ Usuário não encontrado!")

cur.close()
conn.close()

