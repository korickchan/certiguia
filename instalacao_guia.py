"""Guias de instalação por profissão, software e formato de certificado."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

INSTALACAO_DIR = os.path.join(os.path.dirname(__file__), "data", "instalacao")
INDEX_PATH = os.path.join(INSTALACAO_DIR, "index.json")


def _parse_frontmatter(texto: str) -> tuple[dict[str, Any], str]:
    if not texto.startswith("---"):
        return {}, texto
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)", texto, re.S)
    if not m:
        return {}, texto
    meta: dict[str, Any] = {}
    for linha in m.group(1).splitlines():
        if ":" not in linha:
            continue
        chave, val = linha.split(":", 1)
        meta[chave.strip()] = val.strip().strip('"').strip("'")
    return meta, m.group(2).strip()


def _markdown_para_html(texto: str) -> str:
    try:
        import markdown  # type: ignore

        return markdown.markdown(
            texto,
            extensions=["extra", "sane_lists", "nl2br"],
        )
    except Exception:
        paragrafos = []
        for bloco in re.split(r"\n\s*\n", texto.strip()):
            bloco = bloco.strip()
            if not bloco:
                continue
            if bloco.startswith("## "):
                paragrafos.append(f"<h2>{bloco[3:]}</h2>")
            elif bloco.startswith("### "):
                paragrafos.append(f"<h3>{bloco[4:]}</h3>")
            elif re.match(r"^\d+\.\s", bloco):
                itens = re.findall(r"^\d+\.\s+(.*)$", bloco, re.M)
                lis = "".join(f"<li>{i}</li>" for i in itens)
                paragrafos.append(f"<ol>{lis}</ol>")
            elif bloco.startswith("- "):
                itens = [ln[2:] for ln in bloco.splitlines() if ln.startswith("- ")]
                lis = "".join(f"<li>{i}</li>" for i in itens)
                paragrafos.append(f"<ul>{lis}</ul>")
            else:
                paragrafos.append(f"<p>{bloco}</p>")
        return "\n".join(paragrafos)


@lru_cache(maxsize=1)
def _carregar_index() -> dict:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def chave_formato_instalacao(vet) -> str:
    """Deriva chave do catálogo (ex.: a3-nuvem) a partir do perfil do usuário."""
    from catalogo_precos import filtros_de_vet

    filtro = filtros_de_vet(vet)
    arm = (filtro.armazenamento or "A1").lower()
    midia = (filtro.midia or "").lower().replace("_", "-")
    if not midia:
        midia = "arquivo" if arm == "a1" else "token"
    chave = f"{arm}-{midia}"
    index = _carregar_index()
    if chave in index.get("formatos", {}):
        return chave
    for candidato in (f"{arm}-arquivo", f"{arm}-token", f"{arm}-nuvem", "a1-arquivo"):
        if candidato in index.get("formatos", {}):
            return candidato
    return chave


def rotulo_formato_instalacao(chave: str) -> str:
    index = _carregar_index()
    info = index.get("formatos", {}).get(chave, {})
    return info.get("rotulo") or chave.replace("-", " ").upper()


def profissao_catalogo(profissao: str) -> dict:
    index = _carregar_index()
    prof = (profissao or "outro").strip().lower()
    if prof not in index.get("profissoes", {}):
        prof = "outro"
    return index["profissoes"][prof]


def listar_softwares(profissao: str, formato_chave: str) -> list[dict]:
    """Softwares da profissão compatíveis com o formato de certificado."""
    cat = profissao_catalogo(profissao)
    out: list[dict] = []
    for sw in cat.get("softwares", []):
        formatos = sw.get("formatos") or []
        if formato_chave in formatos:
            out.append({**sw, "formato_ok": True})
    return out


def _caminho_guia(profissao: str, software_id: str, formato: str) -> str | None:
    prof = (profissao or "outro").strip().lower()
    candidatos = [
        os.path.join(INSTALACAO_DIR, prof, software_id, f"{formato}.md"),
        os.path.join(INSTALACAO_DIR, "outro", software_id, f"{formato}.md"),
        os.path.join(INSTALACAO_DIR, "_generico", f"{formato}.md"),
    ]
    for path in candidatos:
        if os.path.isfile(path):
            return path
    return None


def carregar_guia_instalacao(
    profissao: str,
    software_id: str,
    formato_chave: str,
) -> dict | None:
    """Carrega guia Markdown; retorna dict com html, meta, origem."""
    path = _caminho_guia(profissao, software_id, formato_chave)
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    meta, corpo = _parse_frontmatter(raw)
    rel = os.path.relpath(path, INSTALACAO_DIR).replace("\\", "/")
    return {
        "meta": meta,
        "html": _markdown_para_html(corpo),
        "markdown": corpo,
        "arquivo": rel,
        "especifico": not rel.startswith("_generico/"),
    }


def guia_instalacao_vet(vet) -> dict | None:
    """Guia completo para o usuário atual."""
    software_id = getattr(vet, "software_instalacao", None) or ""
    if not software_id:
        return None
    formato = chave_formato_instalacao(vet)
    prof = getattr(vet, "profissao", None) or "outro"
    guia = carregar_guia_instalacao(prof, software_id, formato)
    if not guia:
        return None
    sw_list = listar_softwares(prof, formato)
    sw_info = next((s for s in sw_list if s["id"] == software_id), None)
    guia["software_id"] = software_id
    guia["software_nome"] = (sw_info or {}).get("nome") or software_id
    guia["formato"] = formato
    guia["formato_rotulo"] = rotulo_formato_instalacao(formato)
    guia["profissao"] = prof
    return guia
