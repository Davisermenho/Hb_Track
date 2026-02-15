# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/schema/check_routes_list.py
# HB_SCRIPT_OUTPUTS=stdout
from app.api.v1.routers import exercises

print("Rotas do exercises.router:")
for r in exercises.router.routes:
    methods = ', '.join(r.methods) if hasattr(r, 'methods') else 'N/A'
    print(f"  {r.path:40} {methods}")

