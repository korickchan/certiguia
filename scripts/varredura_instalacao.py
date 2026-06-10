#!/usr/bin/env python3
"""Varredura manual de guias de instalação (documentação oficial → data/instalacao/)."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from varredura_instalacao import (  # noqa: E402
    executar_varredura,
    listar_pendentes,
    listar_tarefas,
    resumo_catalogo,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Busca documentação oficial e gera/atualiza guias Markdown de instalação.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar arquivos")
    parser.add_argument("--profissao", help="Filtrar profissão (ex.: veterinario)")
    parser.add_argument("--software", dest="software_id", help="Filtrar software (ex.: simples_vet)")
    parser.add_argument("--formato", help="Filtrar formato (ex.: a1-arquivo)")
    parser.add_argument(
        "--listar-tarefas",
        action="store_true",
        help="Lista combinações com fontes URL (o que a varredura executaria)",
    )
    parser.add_argument(
        "--listar-pendentes",
        action="store_true",
        help="Lista combinações sem fontes URL (falta preencher index.json)",
    )
    args = parser.parse_args()

    if args.listar_tarefas:
        res = resumo_catalogo()
        print(f"Tarefas configuradas: {res['tarefas']} | Pendentes: {res['pendentes']}\n")
        listar_tarefas()
        return 0

    if args.listar_pendentes:
        res = resumo_catalogo()
        print(f"Tarefas configuradas: {res['tarefas']} | Pendentes: {res['pendentes']}\n")
        listar_pendentes()
        return 0

    print("Varredura de guias de instalação…")
    resultado = executar_varredura(
        dry_run=args.dry_run,
        profissao=args.profissao,
        software_id=args.software_id,
        formato=args.formato,
    )

    if resultado.get("erro"):
        print(f"Erro: {resultado['erro']}")
        return 1

    print(
        f"Tarefas: {resultado.get('tarefas', 0)} | "
        f"Gerados: {resultado['gerados']} | Falhas: {len(resultado.get('falhas', []))}"
    )
    for falha in resultado.get("falhas", []):
        print(
            f"  FALHA {falha.get('profissao')}/{falha.get('software_id')}/"
            f"{falha.get('formato')}: {falha.get('motivo')}"
        )
    if resultado.get("aviso"):
        print(f"Aviso: {resultado['aviso']}")

    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
