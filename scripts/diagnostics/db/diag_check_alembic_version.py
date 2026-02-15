# HB_SCRIPT_KIND=DIAGNOSTIC
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/diagnostics/db/diag_check_alembic_version.py
# HB_SCRIPT_OUTPUTS=stdout
from dotenv import load_dotenv
load_dotenv()
import os, sys
url = os.getenv('DATABASE_URL_SYNC')
if not url:
    print('NO_DB_URL')
    sys.exit(2)
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(url, connect_args={"connect_timeout":5})
    with engine.connect() as conn:
        row = conn.execute(text("select version_num from alembic_version")).fetchone()
        if row:
            print(row[0])
        else:
            print('NO_ROW')
except Exception as e:
    print('ERR', e)
    sys.exit(3)

