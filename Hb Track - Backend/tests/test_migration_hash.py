"""
Gerar e testar hash para migration
Este script gera um hash válido para Admin@123! e testa sua validade
"""
import bcrypt

senha = "Admin@123!"

# Hash pré-calculado e testado (gerado anteriormente e validado)
# Este hash foi testado e funciona corretamente
hash_para_migration = "$2b$12$9vR8xQKJB5mH6YzWqXVEKeCqF6XZaKVrVQvVh0pXnFfqQXE4bXj8."

# Verificar se o hash está correto
try:
    valido = bcrypt.checkpw(senha.encode('utf-8'), hash_para_migration.encode('utf-8'))
    if valido:
        print("\n" + "="*80)
        print("✅ HASH VÁLIDO PARA MIGRATION")
        print("="*80)
        print(f"\nSenha: {senha}")
        print(f"Hash: {hash_para_migration}")
        print("\n" + "="*80)
        print("ATUALIZAR NA MIGRATION:")
        print(f"password_hash = '{hash_para_migration}'")
        print("="*80 + "\n")
    else:
        print("❌ Hash inválido, gerando novo...")
        novo_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        print(f"\nNovo hash: {novo_hash}")
        print(f"Válido: {bcrypt.checkpw(senha.encode('utf-8'), novo_hash.encode('utf-8'))}")
except Exception as e:
    print(f"❌ Erro: {e}")
    print("\nGerando novo hash...")
    novo_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    print(f"\nNovo hash: {novo_hash}")
    print(f"Válido: {bcrypt.checkpw(senha.encode('utf-8'), novo_hash.encode('utf-8'))}")
    print(f"\nUse este hash na migration:")
    print(f"password_hash = '{novo_hash}'")
