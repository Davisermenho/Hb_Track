#!/usr/bin/env python
"""Test if api.py can import exercises router"""
import sys

try:
    print("1. Importing exercises router...")
    from app.api.v1.routers import exercises
    print(f"   OK - {len(exercises.router.routes)} routes")
    
    print("\n2. Importing api.py...")
    from app.api.v1 import api
    print(f"   OK")
    
    print("\n3. Checking routes in api_router...")
    all_routes = list(api.api_router.routes)
    print(f"   Total routes: {len(all_routes)}")
    
    exercise_routes = [r.path for r in all_routes if 'exercise' in r.path.lower()]
    print(f"   Exercise routes: {len(exercise_routes)}")
    
    if exercise_routes:
        print("\n[OK] Exercise routes found:")
        for route in exercise_routes:
            print(f"     - {route}")
    else:
        print("\n[FAIL] NO EXERCISE ROUTES IN API_ROUTER!")
        print("\n   First 20 routes:")
        for route in all_routes[:20]:
            print(f"     - {route.path}")
    
    sys.exit(0 if exercise_routes else 1)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(2)
