from app.api.v1 import api

print('✓ API router carregado')
all_routes = list(api.api_router.routes)
print(f'Total rotas: {len(all_routes)}')

exercise_routes = [r.path for r in all_routes if 'exercise' in r.path.lower()]
print(f'\nRotas exercises: {len(exercise_routes)}')
for r in exercise_routes:
    print(f'  - {r}')

if len(exercise_routes) == 0:
    print('\n⚠️ NENHUMA ROTA DE EXERCISES ENCONTRADA!')
    print('\nPrimeiras 10 rotas:')
    for r in all_routes[:10]:
        print(f'  - {r.path}')
