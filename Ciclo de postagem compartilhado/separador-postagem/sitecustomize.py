from pathlib import Path
import sys

local_packages = Path(__file__).with_name(".python_packages")

try:
    list(local_packages.iterdir())
    pacote_pypdf = local_packages / "pypdf" / "__init__.py"
    try:
        with pacote_pypdf.open("rb"):
            pass
    except FileNotFoundError:
        pass
    pode_usar_pacotes_locais = local_packages.exists()
except OSError:
    pode_usar_pacotes_locais = False

if pode_usar_pacotes_locais:
    path = str(local_packages)
    if path not in sys.path:
        sys.path.insert(0, path)
