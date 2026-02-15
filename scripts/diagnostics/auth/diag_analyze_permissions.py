# HB_SCRIPT_KIND=DIAGNOSTIC
# HB_SCRIPT_SCOPE=auth
# HB_SCRIPT_SIDE_EFFECTS=FS_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=scripts/diagnostics/auth/analyze_permissions.py
# HB_SCRIPT_OUTPUTS=stdout
# HB_SCRIPT_INPUTS=repo_files
# HB_SCRIPT_RISK=low
# HB_SCRIPT_ROLLBACK=none

"""Analisar permissions_map.py e gerar matriz RBAC correta."""
import sys
sys.path.insert(0, 'Hb Track - Backend')
from app.core.permissions_map import ROLE_PERMISSIONS, get_all_permission_keys

# Contar permissões por role
print('=' * 70)
print('ANÁLISE DO PERMISSIONS_MAP.PY (FONTE CANÔNICA)')
print('=' * 70)
print()

# Total de permissões únicas
all_perms = get_all_permission_keys()
print(f'📊 Total de permissões únicas definidas: {len(all_perms)}')
print()

# Contagem por role
print('📋 Distribuição de permissões por role:')
print('-' * 70)
print(f'{"Role":<15} | {"Total":<6} | {"True (habilitadas)":<18} | {"False":<6}')
print('-' * 70)

role_summary = {}
for role, perms in ROLE_PERMISSIONS.items():
    true_count = sum(1 for v in perms.values() if v is True)
    false_count = sum(1 for v in perms.values() if v is False)
    total = len(perms)
    role_summary[role] = true_count
    print(f'{role:<15} | {total:<6} | {true_count:<18} | {false_count:<6}')

print('-' * 70)
total_true = sum(role_summary.values())
print(f'{"TOTAL":<15} | {"":<6} | {total_true:<18} | ')
print()

# Comparar com expectativa do documento
print('=' * 70)
print('COMPARAÇÃO COM SCHEMA_CANONICO_DATABASE.MD')
print('=' * 70)
expected = {
    'dirigente': 61,
    'coordenador': 58,
    'treinador': 46,
    'atleta': 32,
    'membro': 12
}

print(f'{"Role":<15} | {"Real":<6} | {"Esperado":<10} | {"Diferença":<10} | {"Status"}')
print('-' * 70)
all_match = True
for role in ['dirigente', 'coordenador', 'treinador', 'atleta', 'membro']:
    real = role_summary.get(role, 0)
    exp = expected.get(role, 0)
    diff = real - exp
    status = '✅' if diff == 0 else '❌'
    if diff != 0:
        all_match = False
    print(f'{role:<15} | {real:<6} | {exp:<10} | {diff:+10} | {status}')

print('-' * 70)
real_total = sum(role_summary.get(r, 0) for r in expected.keys())
exp_total = sum(expected.values())
print(f'{"TOTAL":<15} | {real_total:<6} | {exp_total:<10} | {real_total - exp_total:+10} |')
print()

if all_match:
    print('✅ TODOS OS VALORES CORRESPONDEM AO DOCUMENTO!')
else:
    print('❌ VALORES NÃO CORRESPONDEM - DOCUMENTO ESTÁ DESATUALIZADO!')
    print()
    print('🔧 AÇÃO REQUERIDA:')
    print('   1. Atualizar SCHEMA_CANONICO_DATABASE.md com valores reais')
    print('   2. OU ajustar permissions_map.py se valores esperados estiverem corretos')

print()
print('=' * 70)
print('LISTA DE TODAS AS PERMISSÕES ({} total):'.format(len(all_perms)))
print('=' * 70)
for i, perm in enumerate(all_perms, 1):
    print(f'{i:2}. {perm}')

print()
print('=' * 70)
print('MATRIZ COMPLETA PARA MIGRATION')
print('=' * 70)
print()
print('# Gerar role_permissions para migration:')
print('role_permissions_data = []')
print('permission_id = 1')
print()

for role_id, (role_code, perms) in enumerate(ROLE_PERMISSIONS.items(), 1):
    if role_code == 'superadmin':
        continue  # Superadmin não está na tabela roles
    
    true_perms = [k for k, v in perms.items() if v is True]
    print(f'# {role_code.capitalize()} (role_id={role_id}) - {len(true_perms)} permissões')
    print(f'for perm_code in {true_perms[:3]}:  # ... ({len(true_perms)} total)')
    print(f'    role_permissions_data.append((')
    print(f'        {role_id},  # role_id ({role_code})')
    print(f'        permission_id,  # permission_id')
    print(f'    ))')
    print(f'    permission_id += 1')
    print()
