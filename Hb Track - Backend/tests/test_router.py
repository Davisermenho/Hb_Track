from app.api.v1.routers import exercises

routes = [r.path for r in exercises.router.routes]
print(f'✓ Router carregado com {len(routes)} rotas:')
for r in sorted(set(routes)):
    print(f'  - {r}')
