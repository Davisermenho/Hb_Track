# HB_SCRIPT_KIND=FIX
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/fixes/db/fix_migrations.py
# HB_SCRIPT_OUTPUTS=stdout
import os
import re

versions_dir = r"C:\HB TRACK\Hb Track - Backend\db\alembic\versions"

for filename in sorted(os.listdir(versions_dir)):
    if filename.startswith("00") and filename.endswith(".py"):
        filepath = os.path.join(versions_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extrair número da migration do nome do arquivo
        match = re.match(r'(\d{4})_', filename)
        if not match:
            continue
        
        new_rev_id = match.group(1)
        
        # Verificar se precisa correção
        if f"revision: str = '{new_rev_id}'" in content or f"revision = '{new_rev_id}'" in content:
            print(f"✓ {filename}: já correto ({new_rev_id})")
            continue
        
        # Corrigir revision
        content = re.sub(
            r"(revision:\s*(?:str\s*)?=\s*['\"])[^'\"]+(['\"])",
            rf"\1{new_rev_id}\2",
            content,
            count=1
        )
        
        # Corrigir down_revision para usar número simples
        if new_rev_id != "0001":  # primeira migration não tem down_revision anterior
            prev_rev = f"{int(new_rev_id) - 1:04d}"
            content = re.sub(
                r"(down_revision:\s*(?:Union\[str,\s*(?:Sequence\[str\],?\s*)?None\]\s*)?=\s*(?:\()?['\"])[^'\"]+(['\"](?:\))?)",
                rf"\1{prev_rev}\2",
                content,
                count=1
            )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ {filename}: corrigido para {new_rev_id}")

print("\n✅ Todas as migrations corrigidas!")

