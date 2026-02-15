# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/db/check_athletes_columns.py
# HB_SCRIPT_OUTPUTS=stdout
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='athletes' 
    ORDER BY ordinal_position
""")

print("Colunas da tabela athletes:")
print("-" * 50)
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

conn.close()

