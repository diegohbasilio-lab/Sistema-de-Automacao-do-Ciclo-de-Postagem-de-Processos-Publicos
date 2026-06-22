import getpass
import json
from pathlib import Path


arquivo = Path(__file__).with_name("credenciais_login.json")

email = input("E-mail: ").strip()
senha = getpass.getpass("Senha: ")

if not email or not senha:
    raise SystemExit("E-mail e senha são obrigatórios.")

arquivo.write_text(
    json.dumps({"email": email, "senha": senha}, ensure_ascii=False, indent=4),
    encoding="utf-8",
)

print(f"Credenciais salvas em: {arquivo}")
