#!/usr/bin/env python3
"""
Compat shim: `python scripts/verify_automatica.py` == `python verify_automatica.py`
Manté compatibilitat amb AGENTS.md (scripts/) i amb l'ús real (root).
"""

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "verify_automatica.py"

if not TARGET.exists():
    print(f"ERROR: {TARGET} no encontrado", file=sys.stderr)
    sys.exit(1)

# Executar el verify real com a __main__
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
