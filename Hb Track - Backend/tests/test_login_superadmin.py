"""
Testar login do superadmin
"""
import requests

BASE_URL = "http://localhost:8000"

# Dados de login
login_data = {
    "username": "adm@handballtrack.app",
    "password": "Admin@123!"
}

print("\n" + "="*70)
print("TESTE DE LOGIN SUPERADMIN")
print("="*70)
print(f"\nEmail: {login_data['username']}")
print(f"Senha: {login_data['password']}\n")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ LOGIN BEM-SUCEDIDO!")
        print(f"\nToken: {data.get('access_token', 'N/A')[:50]}...")
        print(f"Token Type: {data.get('token_type', 'N/A')}")
        print("="*70 + "\n")
    else:
        print(f"\n❌ LOGIN FALHOU!")
        print(f"Resposta: {response.text}")
        print("="*70 + "\n")
        
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("="*70 + "\n")
