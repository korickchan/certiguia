#!/usr/bin/env python3
"""Varredura manual do catálogo + exportação do seed JSON."""
import os
import sys

os.environ.setdefault("CATALOGO_VARREDURA_INICIO", "0")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import PrecoCatalogo, app  # noqa: E402
from catalogo_precos import (  # noqa: E402
    _executar_varredura,
    exportar_catalogo_seed,
    info_catalogo,
)


def main() -> int:
    with app.app_context():
        print("Varredura do catálogo de preços…")
        _executar_varredura()
        info = info_catalogo()
        total = PrecoCatalogo.query.count()
        print(f"Status: {info['status']} | Itens: {total}")
        if info.get("ultima_varredura"):
            print(f"Concluída: {info['ultima_varredura']}")
        n = exportar_catalogo_seed()
        print(f"Seed exportado: data/catalogo_seed.json ({n} itens)")
        return 0 if info["status"] == "ok" and total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
