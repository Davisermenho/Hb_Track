# HB_SCRIPT_KIND=DIAGNOSTIC
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_READ
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/diagnostics/db/diag_decode_token.py
# HB_SCRIPT_OUTPUTS=stdout
import json
import jwt

# Ler token do coordenador
with open(r'C:\HB TRACK\Hb Track - Fronted\playwright\.auth\coordenador.json', 'r') as f:
    data = json.load(f)
    token = next((c['value'] for c in data['cookies'] if c['name'] == 'hb_access_token'), None)

if token:
    # Decodificar (sem verificar assinatura)
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("=== TOKEN DO COORDENADOR ===")
    print(json.dumps(decoded, indent=2))
    print(f"\nOrganization ID no token: {decoded.get('organization_id')}")
    print(f"Membership ID no token: {decoded.get('membership_id')}")
    print(f"Role no token: {decoded.get('role_code')}")
else:
    print("Token não encontrado")

