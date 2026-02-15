import bcrypt

hash_banco = r"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqgdXnGV8W"
senha = "Admin@123!"

print("Hash no banco:", hash_banco)
print("Senha testada:", senha)
print("Resultado:", bcrypt.checkpw(senha.encode('utf-8'), hash_banco.encode('utf-8')))
