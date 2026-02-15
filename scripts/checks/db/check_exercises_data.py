# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/db/check_exercises_data.py
# HB_SCRIPT_OUTPUTS=stdout
"""Verificar dados de exercícios no banco."""
import asyncio
from app.core.db import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM exercise_tags'))
        count1 = result.scalar()
        print(f'exercise_tags: {count1} registros')
        
        result2 = await conn.execute(text('SELECT COUNT(*) FROM exercises'))
        count2 = result2.scalar()
        print(f'exercises: {count2} registros')
        
        result3 = await conn.execute(text('SELECT name FROM exercise_tags LIMIT 5'))
        rows = result3.fetchall()
        print(f'Tags existentes: {[r[0] for r in rows]}')

asyncio.run(check())

