# HB_SCRIPT_KIND=GENERATE
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=FS_WRITE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/generate/schema/gen_migration_hash.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Gerar hash bcrypt determinístico para usar na migration
"""
import bcrypt

senha = "Admin@123!"

# Gerar hash com um salt específico para ser determinístico
# Isso garante que o hash será sempre o mesmo
salt = bcrypt.gensalt(rounds=12)
hash_gerado = bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

print("\n" + "="*70)
print("HASH BCRYPT PARA MIGRATION")
print("="*70)
print(f"\nSenha: {senha}")
print(f"Hash: {hash_gerado}")
print(f"\nVerificação: {bcrypt.checkpw(senha.encode('utf-8'), hash_gerado.encode('utf-8'))}")
print("="*70)
print("\nCopie este hash para a migration 0041_add_complete_rbac_system.py")
print("="*70 + "\n")

