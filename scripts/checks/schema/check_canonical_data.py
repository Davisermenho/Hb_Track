# HB_SCRIPT_KIND=CHECK
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/checks/schema/check_canonical_data.py
# HB_SCRIPT_OUTPUTS=stdout
"""Verificar se os dados canônicos foram populados corretamente."""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from pathlib import Path

# Carregar .env do diretório backend
env_path = Path(__file__).parent / 'Hb Track - Backend' / '.env'
load_dotenv(env_path)
db_url = os.getenv('DATABASE_URL_SYNC')  # Usar versão síncrona para scripts

if not db_url:
    print(f'❌ DATABASE_URL_SYNC não encontrado no .env: {env_path}')
    exit(1)

engine = create_engine(db_url)

with engine.connect() as conn:
    print('========================================')
    print('VERIFICAÇÃO DO SCHEMA CANÔNICO')
    print('========================================\n')
    
    # Roles
    result = conn.execute(text('SELECT COUNT(*) FROM roles'))
    roles_count = result.scalar()
    print(f'✓ roles: {roles_count} registros')
    
    # Categories
    result = conn.execute(text('SELECT COUNT(*) FROM categories'))
    categories_count = result.scalar()
    print(f'✓ categories: {categories_count} registros')
    
    # Permissions
    result = conn.execute(text('SELECT COUNT(*) FROM permissions'))
    permissions_count = result.scalar()
    print(f'✓ permissions: {permissions_count} registros')
    
    # Role Permissions
    result = conn.execute(text('SELECT COUNT(*) FROM role_permissions'))
    role_permissions_count = result.scalar()
    print(f'✓ role_permissions: {role_permissions_count} registros')
    
    # Offensive Positions
    result = conn.execute(text('SELECT COUNT(*) FROM offensive_positions'))
    offensive_count = result.scalar()
    print(f'✓ offensive_positions: {offensive_count} registros')
    
    # Defensive Positions
    result = conn.execute(text('SELECT COUNT(*) FROM defensive_positions'))
    defensive_count = result.scalar()
    print(f'✓ defensive_positions: {defensive_count} registros')
    
    # Schooling Levels
    result = conn.execute(text('SELECT COUNT(*) FROM schooling_levels'))
    schooling_count = result.scalar()
    print(f'✓ schooling_levels: {schooling_count} registros')
    
    # Phases of Play
    result = conn.execute(text('SELECT COUNT(*) FROM phases_of_play'))
    phases_count = result.scalar()
    print(f'✓ phases_of_play: {phases_count} registros')
    
    # Advantage States
    result = conn.execute(text('SELECT COUNT(*) FROM advantage_states'))
    advantage_count = result.scalar()
    print(f'✓ advantage_states: {advantage_count} registros')
    
    # Event Types
    result = conn.execute(text('SELECT COUNT(*) FROM event_types'))
    event_types_count = result.scalar()
    print(f'✓ event_types: {event_types_count} registros')
    
    # Super Admin
    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE email = 'adm@handballtrack.app'"))
    admin_count = result.scalar()
    print(f'✓ super_admin: {admin_count} usuário')
    
    print('\n========================================')
    print('COMPARAÇÃO COM SCHEMA_CANONICO_DATABASE.md')
    print('========================================\n')
    
    expected = {
        'roles': 5,
        'categories': 7,
        'permissions': 65,
        'role_permissions': 209,
        'offensive_positions': 6,
        'defensive_positions': 5,
        'schooling_levels': 6,
        'phases_of_play': 4,
        'advantage_states': 3,
        'event_types': 11,
        'super_admin': 1
    }
    
    actual = {
        'roles': roles_count,
        'categories': categories_count,
        'permissions': permissions_count,
        'role_permissions': role_permissions_count,
        'offensive_positions': offensive_count,
        'defensive_positions': defensive_count,
        'schooling_levels': schooling_count,
        'phases_of_play': phases_count,
        'advantage_states': advantage_count,
        'event_types': event_types_count,
        'super_admin': admin_count
    }
    
    all_correct = True
    for key, expected_val in expected.items():
        actual_val = actual[key]
        status = '✅' if actual_val == expected_val else '❌'
        print(f'{status} {key}: {actual_val} / {expected_val}')
        if actual_val != expected_val:
            all_correct = False
    
    print()
    if all_correct:
        print('✅ TODOS OS DADOS CANÔNICOS ESTÃO CORRETOS!')
    else:
        print('❌ ALGUNS DADOS NÃO CONFEREM COM O ESPERADO')

