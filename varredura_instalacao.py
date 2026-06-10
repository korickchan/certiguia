"""Varredura de documentação oficial → guias Markdown em data/instalacao/."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent
INSTALACAO_DIR = ROOT / "data" / "instalacao"
INDEX_PATH = INSTALACAO_DIR / "index.json"

_SELETORES_CONTEUDO = (
    "article",
    "main",
    "[role='main']",
    ".article-body",
    ".article__body",
    ".intercom-interblocks",
    "#main-content",
    ".markdown-body",
)


def carregar_index() -> dict:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def salvar_guia(
    profissao: str,
    software_id: str,
    formato: str,
    markdown: str,
    *,
    dry_run: bool = False,
) -> Path:
    path = INSTALACAO_DIR / profissao / software_id / f"{formato}.md"
    if dry_run:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def iter_tarefas_varredura(
    index: dict | None = None,
    *,
    profissao: str | None = None,
    software_id: str | None = None,
    formato: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Gera tarefas (prof, software, formato, url) com fonte configurada."""
    data = index or carregar_index()
    prof_filtro = (profissao or "").strip().lower()
    sw_filtro = (software_id or "").strip().lower()
    fmt_filtro = (formato or "").strip().lower()

    for prof_key, prof_data in data.get("profissoes", {}).items():
        if prof_filtro and prof_key != prof_filtro:
            continue
        for sw in prof_data.get("softwares", []):
            sid = sw.get("id") or ""
            if sw_filtro and sid != sw_filtro:
                continue
            if sid == "outro":
                continue
            fontes = sw.get("fontes") or {}
            for fmt in sw.get("formatos") or []:
                if fmt_filtro and fmt != fmt_filtro:
                    continue
                url = fontes.get(fmt)
                if not url:
                    continue
                yield {
                    "profissao": prof_key,
                    "software_id": sid,
                    "software_nome": sw.get("nome") or sid,
                    "formato": fmt,
                    "url": url,
                    "site": sw.get("site"),
                }


def _texto_limpo(texto: str) -> str:
    texto = re.sub(r"\s+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _html_para_markdown_simples(html: str) -> str:
    """Conversão leve para rascunho automático (revisão humana recomendada)."""
    html = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", "", html)
    html = re.sub(r"(?i)<h1[^>]*>(.*?)</h1>", r"\n# \1\n", html)
    html = re.sub(r"(?i)<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html)
    html = re.sub(r"(?i)<h3[^>]*>(.*?)</h3>", r"\n### \1\n", html)
    html = re.sub(r"(?i)<li[^>]*>(.*?)</li>", r"\n- \1", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n\n", html)
    html = re.sub(r"<[^>]+>", "", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    return _texto_limpo(html)


def extrair_conteudo_pagina(page, url: str) -> dict[str, str]:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(1500)
    titulo = (page.title() or "").strip()
    corpo = ""
    for seletor in _SELETORES_CONTEUDO:
        loc = page.locator(seletor).first
        if loc.count() and loc.is_visible():
            corpo = loc.inner_text(timeout=5_000)
            if len(corpo.strip()) > 120:
                break
    if not corpo.strip():
        corpo = page.locator("body").inner_text(timeout=10_000)
    return {"titulo": titulo, "texto": _texto_limpo(corpo)}


def montar_markdown_guia(
    *,
    profissao: str,
    software_id: str,
    software_nome: str,
    formato: str,
    url: str,
    titulo_pagina: str,
    corpo_extraido: str,
) -> str:
    hoje = date.today().isoformat()
    intro = (
        f"Guia gerado automaticamente a partir da documentação oficial. "
        f"Revise os passos antes de publicar em produção.\n\n"
        f"**Fonte:** [{titulo_pagina or url}]({url})"
    )
    corpo_md = _html_para_markdown_simples(corpo_extraido) if "<" in corpo_extraido else corpo_extraido
    if len(corpo_md) > 6000:
        corpo_md = corpo_md[:6000].rsplit("\n", 1)[0] + "\n\n…"

    return f"""---
software: {software_id}
software_nome: {software_nome}
profissao: {profissao}
formato: {formato}
atualizado: {hoje}
fonte: automacao
fonte_url: {url}
---

## {software_nome} — {formato.replace("-", " ")}

{intro}

### Passos (extraídos da documentação)

{corpo_md}
"""


def iter_pendentes_varredura(index: dict | None = None) -> Iterator[dict[str, Any]]:
    """Software/formato sem URL em fontes (candidatos a preencher no index.json)."""
    data = index or carregar_index()
    for prof_key, prof_data in data.get("profissoes", {}).items():
        for sw in prof_data.get("softwares", []):
            sid = sw.get("id") or ""
            if sid == "outro":
                continue
            fontes = sw.get("fontes") or {}
            for fmt in sw.get("formatos") or []:
                if not fontes.get(fmt):
                    yield {
                        "profissao": prof_key,
                        "software_id": sid,
                        "software_nome": sw.get("nome") or sid,
                        "formato": fmt,
                        "site": sw.get("site"),
                    }


def resumo_catalogo(index: dict | None = None) -> dict[str, int]:
    data = index or carregar_index()
    tarefas = list(iter_tarefas_varredura(data))
    pendentes = list(iter_pendentes_varredura(data))
    return {
        "tarefas": len(tarefas),
        "pendentes": len(pendentes),
    }


def listar_pendentes() -> None:
    for item in iter_pendentes_varredura():
        site = f" | site: {item['site']}" if item.get("site") else ""
        print(
            f"  {item['profissao']}/{item['software_id']}/{item['formato']}"
            f" - {item['software_nome']}{site}"
        )


def listar_tarefas() -> None:
    for t in iter_tarefas_varredura():
        print(f"  {t['profissao']}/{t['software_id']}/{t['formato']} -> {t['url']}")


def executar_varredura(
    *,
    dry_run: bool = False,
    profissao: str | None = None,
    software_id: str | None = None,
    formato: str | None = None,
) -> dict[str, Any]:
    from buscar_precos import playwright_disponivel

    if not playwright_disponivel():
        return {
            "ok": False,
            "erro": "Playwright indisponível. Rode: pip install playwright && playwright install chromium",
            "gerados": 0,
            "ignorados": 0,
            "falhas": [],
        }

    tarefas = list(
        iter_tarefas_varredura(
            profissao=profissao,
            software_id=software_id,
            formato=formato,
        )
    )
    if not tarefas:
        return {
            "ok": True,
            "gerados": 0,
            "ignorados": 0,
            "falhas": [],
            "aviso": "Nenhuma tarefa com fontes URL configuradas.",
        }

    from playwright.sync_api import sync_playwright

    gerados = 0
    falhas: list[dict[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            for t in tarefas:
                try:
                    conteudo = extrair_conteudo_pagina(page, t["url"])
                    if len(conteudo["texto"]) < 80:
                        falhas.append(
                            {
                                **{k: t[k] for k in ("profissao", "software_id", "formato", "url")},
                                "motivo": "conteúdo insuficiente na página",
                            }
                        )
                        continue
                    md = montar_markdown_guia(
                        profissao=t["profissao"],
                        software_id=t["software_id"],
                        software_nome=t["software_nome"],
                        formato=t["formato"],
                        url=t["url"],
                        titulo_pagina=conteudo["titulo"],
                        corpo_extraido=conteudo["texto"],
                    )
                    path = salvar_guia(
                        t["profissao"],
                        t["software_id"],
                        t["formato"],
                        md,
                        dry_run=dry_run,
                    )
                    gerados += 1
                    print(f"{'[dry-run] ' if dry_run else ''}OK {path.relative_to(ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    falhas.append(
                        {
                            **{k: t[k] for k in ("profissao", "software_id", "formato", "url")},
                            "motivo": str(exc)[:200],
                        }
                    )
        finally:
            browser.close()

    return {
        "ok": gerados > 0 or not falhas,
        "gerados": gerados,
        "ignorados": len(tarefas) - gerados - len(falhas),
        "falhas": falhas,
        "tarefas": len(tarefas),
    }
