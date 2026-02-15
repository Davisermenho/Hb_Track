"""Simula o que main.py faz ao inicializar"""
import logging
logging.basicConfig(level=logging.DEBUG)

print("1. Importing api_router from app.api.v1...")
try:
    from app.api.v1 import api_router
    print(f"   OK - api_router imported")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n2. Checking routes in api_router...")
all_routes = list(api_router.routes)
print(f"   Total routes: {len(all_routes)}")

exercise_routes = [r for r in all_routes if 'exercise' in r.path.lower()]
print(f"   Exercise routes: {len(exercise_routes)}")

if len(exercise_routes) > 0:
    print("\n[SUCCESS] Exercise routes are in api_router:")
    for r in exercise_routes:
        methods = ', '.join(r.methods) if hasattr(r, 'methods') else 'N/A'
        print(f"     {r.path:40} {methods}")
else:
    print("\n[FAIL] NO exercise routes in api_router!")
    print("\n   Sample of first 15 routes:")
    for r in all_routes[:15]:
        print(f"     {r.path}")
