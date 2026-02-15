# HB_SCRIPT_KIND=GENERATE
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=FS_WRITE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/generate/schema/gen_migration_0041.py
# HB_SCRIPT_OUTPUTS=stdout
"""Gerar dados corretos para migration 0041 baseado em permissions_map.py"""
import sys
sys.path.insert(0, 'Hb Track - Backend')
from app.core.permissions_map import ROLE_PERMISSIONS, get_all_permission_keys

# Mapear role_code para role_id
ROLE_ID_MAP = {
    'dirigente': 1,
    'coordenador': 2,
    'treinador': 3,
    'atleta': 4,
    'membro': 5
}

# Obter todas as permissões únicas
all_permissions = get_all_permission_keys()
print(f"# Total de permissões: {len(all_permissions)}")
print()

# Gerar SQL para permissions
print("# =========================================================================")
print("# 1. PERMISSIONS (61 registros)")
print("# =========================================================================")
print("op.execute(\"\"\"")
print("    INSERT INTO permissions (id, code, description, created_at, updated_at)")
print("    VALUES")

for i, perm_code in enumerate(all_permissions, 1):
    comma = "," if i < len(all_permissions) else ""
    print(f"    ({i}, '{perm_code}', '{perm_code.replace('_', ' ').title()}', NOW(), NOW()){comma}")

print("    ON CONFLICT (id) DO NOTHING;")
print("\"\"\")")
print()

# Contar e gerar role_permissions
print("# =========================================================================")
print("# 2. ROLE_PERMISSIONS (220 registros)")
print("# =========================================================================")

total_rp = 0
rp_lines = []

for role_code, role_id in ROLE_ID_MAP.items():
    role_perms = ROLE_PERMISSIONS[role_code]
    true_perms = [perm for perm, enabled in role_perms.items() if enabled]
    
    print(f"# {role_code.capitalize()} (role_id={role_id}): {len(true_perms)} permissões")
    
    for perm_code in true_perms:
        # Encontrar permission_id
        perm_id = all_permissions.index(perm_code) + 1
        rp_lines.append(f"    ({role_id}, {perm_id})")
        total_rp += 1

print()
print(f"# Total role_permissions: {total_rp}")
print()
print("op.execute(\"\"\"")
print("    INSERT INTO role_permissions (role_id, permission_id)")
print("    VALUES")
print(",\n".join(rp_lines))
print("    ON CONFLICT (role_id, permission_id) DO NOTHING;")
print("\"\"\")")
print()

# Summary
print("# =========================================================================")
print("# RESUMO")
print("# =========================================================================")
print(f"# Permissions: {len(all_permissions)}")
print(f"# Role_permissions: {total_rp}")
print("# Roles:")
for role_code, role_id in ROLE_ID_MAP.items():
    role_perms = ROLE_PERMISSIONS[role_code]
    true_count = sum(1 for enabled in role_perms.values() if enabled)
    print(f"#   {role_code}: {true_count}")

