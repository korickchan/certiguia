"""Varredura completa do catálogo com Playwright — todas as combinações de preço."""

from __future__ import annotations

import re
from typing import Any

from certificado import certificadoras_ativas, url_certificadora
from recomendacao import PRODUTOS

CatalogoLinha = dict[str, Any]


def _dedupe_linhas(linhas: list[CatalogoLinha]) -> list[CatalogoLinha]:
    vistos: set[tuple] = set()
    out: list[CatalogoLinha] = []
    for row in linhas:
        chave = (
            row["certificadora"],
            row["produto_tipo"],
            row["categoria"],
            row["armazenamento"],
            row.get("midia") or "",
            row.get("emissao") or "",
            row.get("validade_anos") or 1,
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(row)
    return out


def _linhas_safeweb(produtos: list, categoria: str) -> list[CatalogoLinha]:
    from buscar_precos import _emissao_videoconferencia, _valor_valido

    def _midia(val: str | None) -> str:
        if not val:
            return ""
        v = val.lower()
        if "mobile" in v and "id" in v.replace("-", ""):
            return "mobileid"
        if "mobile" in v or ("mobil" in v and "id" in v):
            return "mobileid"
        if "nuvem" in v or "hsm" in v:
            return "nuvem"
        if "arquivo" in v:
            return "arquivo"
        if "token" in v:
            return "token"
        if "cart" in v:
            return "cartao"
        if "sem" in v:
            return "sem_midia"
        return v

    url_base = url_certificadora("safeweb", "A1", categoria)
    linhas: list[CatalogoLinha] = []
    for item in produtos:
        if item.get("idAcessorio") or item.get("idTipoUsoSafeId"):
            continue
        produto_tipo = item.get("ProdutoTipo") or ""
        if produto_tipo not in ("e-CPF", "e-CNPJ"):
            continue
        modelo = item.get("ProdutoModelo") or ""
        if modelo not in ("A1", "A3"):
            continue
        valor = item.get("Valor")
        if valor is None:
            continue
        valor = float(valor)
        if not _valor_valido(valor, modelo, categoria):
            continue
        validade = int(item.get("Validade") or 1)
        midia = _midia(item.get("MidiaTipo"))
        emissao = "videoconferencia" if _emissao_videoconferencia(item) else "outro"
        linhas.append({
            "certificadora": "safeweb",
            "produto_tipo": produto_tipo,
            "categoria": categoria,
            "armazenamento": modelo,
            "midia": midia,
            "emissao": emissao,
            "validade_anos": validade,
            "preco": valor,
            "url": url_base,
            "observacao": (
                f"Safeweb — {produto_tipo} {modelo}, {item.get('MidiaTipo') or '—'}, "
                f"{item.get('TipoEmissao') or '—'}, {validade} ano(s)."
            ),
            "fonte": "safeweb_playwright",
        })
    return linhas


def _linhas_serpro(page) -> list[CatalogoLinha]:
    from buscar_precos import (
        SERPRO_FILTROS,
        SERPRO_LOJA_URL,
        _normalizar_texto,
        _parse_valor_br,
        _serpro_desmarcar_filtros,
        _valor_valido,
    )

    linhas: list[CatalogoLinha] = []
    page.goto(SERPRO_LOJA_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)

    midias_a1 = [("Arquivo", "arquivo"), ("Nuvem", "nuvem")]
    midias_a3 = [("Somente o Certificado", "sem_midia"), ("Nuvem", "nuvem")]
    validades = [("1 ano", 1), ("2 anos", 2)]

    for categoria in ("pf", "pj"):
        produto_tipo = "e-CPF" if categoria == "pf" else "e-CNPJ"
        for tipo in ("A1", "A3"):
            midias = midias_a1 if tipo == "A1" else midias_a3
            for midia_label, midia_key in midias:
                for val_label, val_anos in validades:
                    try:
                        _serpro_desmarcar_filtros(page)
                        page.get_by_label(SERPRO_FILTROS[categoria], exact=True).check()
                        page.get_by_label(midia_label, exact=True).check()
                        page.get_by_label(val_label, exact=True).check()
                        page.wait_for_timeout(1400)
                    except Exception:
                        continue

                    familia = produto_tipo
                    texto = _normalizar_texto(page.inner_text("body"))
                    padrao = (
                        rf"{familia}\s*\|\s*{tipo}\s*-\s*\d+\s*ano[s]?"
                        rf"[\s\S]{{0,280}}?"
                        rf"R\$\s*([\d.,]+)"
                    )
                    m = re.search(padrao, texto, re.I)
                    if not m:
                        continue
                    preco = _parse_valor_br(m.group(1))
                    if not _valor_valido(preco, tipo, categoria):
                        continue
                    linhas.append({
                        "certificadora": "serpro",
                        "produto_tipo": produto_tipo,
                        "categoria": categoria,
                        "armazenamento": tipo,
                        "midia": midia_key,
                        "emissao": "videoconferencia",
                        "validade_anos": val_anos,
                        "preco": preco,
                        "url": SERPRO_LOJA_URL,
                        "observacao": (
                            f"Serpro — {SERPRO_FILTROS[categoria]}, {midia_label}, {val_label}."
                        ),
                        "fonte": "serpro_playwright",
                    })
    return linhas


def _linhas_valid_playwright(page) -> list[CatalogoLinha]:
    """Visita páginas de produto Valid e confirma variantes/preços."""
    from buscar_precos import (
        VALID_BASE,
        _valid_all_products,
        _valid_produto_tipo,
        _valid_armazenamento,
        _valid_midia_from_product,
        _valid_validade_anos,
        _valor_valido,
    )

    linhas: list[CatalogoLinha] = []
    for product in _valid_all_products():
        handle = product["handle"]
        title = product.get("title") or handle
        if "+" in title or "combo" in handle.lower():
            continue
        tip = _valid_produto_tipo(handle, title)
        if not tip:
            continue
        produto_tipo, categoria = tip
        arm = _valid_armazenamento(handle, title)
        if not arm:
            continue
        midia = _valid_midia_from_product(handle, title, arm)
        url = f"{VALID_BASE}/products/{handle}"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
        except Exception:
            pass

        for v in product.get("variants") or []:
            va = _valid_validade_anos(v.get("title") or "")
            if va is None:
                continue
            try:
                preco = float(v["price"])
            except (KeyError, TypeError, ValueError):
                continue
            if not _valor_valido(preco, arm, categoria):
                continue
            emissao = "renovacao" if "renov" in handle else "videoconferencia"
            linhas.append({
                "certificadora": "valid",
                "produto_tipo": produto_tipo,
                "categoria": categoria,
                "armazenamento": arm,
                "midia": midia,
                "emissao": emissao,
                "validade_anos": va,
                "preco": preco,
                "url": url,
                "observacao": f"Valid — {title}, variante «{v.get('title')}».",
                "fonte": "valid_playwright",
            })
    return linhas


def _linhas_loja_playwright(page, cert_key: str) -> list[CatalogoLinha]:
    """Varre loja genérica com Playwright (cards visíveis na página)."""
    from buscar_precos import (
        _extrair_preco_html,
        _html_para_texto,
        _normalizar_texto,
        _parse_valor_br,
        _valor_valido,
    )

    linhas: list[CatalogoLinha] = []
    cert = certificadoras_ativas().get(cert_key)
    if not cert:
        return linhas

    for produto_id, produto in PRODUTOS.items():
        tipo = produto["tipo_armazenamento"]
        categoria = produto["categoria"]
        chave = produto["chave_preco"]
        url = url_certificadora(cert_key, tipo, categoria)
        produto_tipo = "e-CPF" if categoria == "pf" else "e-CNPJ"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=55000)
            page.wait_for_timeout(5000)
            for _ in range(4):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(400)
            html = page.content()
        except Exception:
            continue

        preco, metodo = _extrair_preco_html(cert_key, html, chave, tipo, categoria)
        if preco and _valor_valido(preco, tipo, categoria):
            midia = "arquivo" if tipo == "A1" else "token"
            linhas.append({
                "certificadora": cert_key,
                "produto_tipo": produto_tipo,
                "categoria": categoria,
                "armazenamento": tipo,
                "midia": midia,
                "emissao": "videoconferencia",
                "validade_anos": 1,
                "preco": preco,
                "url": url,
                "observacao": f"{cert['nome']} — {produto['nome']} ({metodo}).",
                "fonte": f"{cert_key}_playwright",
            })

        texto = _normalizar_texto(_html_para_texto(html))
        familia = "cpf" if categoria == "pf" else "cnpj"
        for midia_pat, midia_key in (
            (rf"e-{familia}\s*{tipo.lower()}[^.]{{0,120}}mobile\s*id[^.]{{0,120}}R\$\s*([\d.,]+)", "mobileid"),
            (rf"mobile\s*id[^.]{{0,120}}e-{familia}\s*{tipo.lower()}[^.]{{0,120}}R\$\s*([\d.,]+)", "mobileid"),
            (rf"e-{familia}\s*{tipo.lower()}[^.]{{0,120}}nuvem[^.]{{0,120}}R\$\s*([\d.,]+)", "nuvem"),
            (rf"nuvem[^.]{{0,120}}e-{familia}\s*{tipo.lower()}[^.]{{0,120}}R\$\s*([\d.,]+)", "nuvem"),
            (rf"e-{familia}\s*{tipo.lower()}[^.]{{0,120}}token[^.]{{0,120}}R\$\s*([\d.,]+)", "token"),
            (rf"e-{familia}\s*{tipo.lower()}[^.]{{0,120}}cart[aã]o[^.]{{0,120}}R\$\s*([\d.,]+)", "cartao"),
        ):
            m = re.search(midia_pat, texto, re.I | re.S)
            if not m:
                continue
            val = _parse_valor_br(m.group(1))
            if val and _valor_valido(val, tipo, categoria):
                linhas.append({
                    "certificadora": cert_key,
                    "produto_tipo": produto_tipo,
                    "categoria": categoria,
                    "armazenamento": tipo,
                    "midia": midia_key,
                    "emissao": "videoconferencia",
                    "validade_anos": 1,
                    "preco": val,
                    "url": url,
                    "observacao": f"{cert['nome']} — {produto_tipo} {tipo} {midia_key} (texto da página).",
                    "fonte": f"{cert_key}_playwright",
                })
    return linhas


def _linhas_acdigital(page) -> list[CatalogoLinha]:
    from buscar_precos import _extrair_preco_acdigital

    linhas: list[CatalogoLinha] = []
    url = url_certificadora("acdigital", "A1", "pf")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
    except Exception:
        return linhas

    for categoria in ("pf", "pj"):
        for tipo in ("A1", "A3"):
            preco = _extrair_preco_acdigital(page, tipo, categoria)
            if not preco:
                continue
            produto_tipo = "e-CPF" if categoria == "pf" else "e-CNPJ"
            linhas.append({
                "certificadora": "acdigital",
                "produto_tipo": produto_tipo,
                "categoria": categoria,
                "armazenamento": tipo,
                "midia": "arquivo" if tipo == "A1" else "sem_midia",
                "emissao": "presencial",
                "validade_anos": 1,
                "preco": preco,
                "url": url,
                "observacao": f"AC Digital — {produto_tipo} {tipo}, emissão presencial.",
                "fonte": "acdigital_playwright",
            })
    return linhas


def coletar_catalogo_completo(browser=None) -> list[CatalogoLinha]:
    """
    Coleta preços de todas as certificadoras (Playwright + APIs).
    Inclui combinações de mídia (arquivo, nuvem, mobileid, token, cartão) e validade.
    """
    from buscar_precos import (
        _launch_chromium,
        _scrape_safeweb_catalogo,
        valid_catalogo_itens,
    )

    linhas: list[CatalogoLinha] = []

    for item in valid_catalogo_itens():
        item["fonte"] = item.get("fonte") or "valid_shopify"
        linhas.append(item)

    own_browser = browser is None
    playwright_ctx = None
    if own_browser:
        from playwright.sync_api import sync_playwright

        playwright_ctx = sync_playwright().start()
        browser = _launch_chromium(playwright_ctx)

    try:
        for categoria in ("pf", "pj"):
            produtos = _scrape_safeweb_catalogo(categoria, browser=browser)
            if produtos:
                linhas.extend(_linhas_safeweb(produtos, categoria))

        page = browser.new_page()
        try:
            linhas.extend(_linhas_serpro(page))
            linhas.extend(_linhas_valid_playwright(page))
            linhas.extend(_linhas_acdigital(page))

            skip = {"safeweb", "serpro", "valid", "acdigital"}
            for cert_key in certificadoras_ativas():
                if cert_key in skip:
                    continue
                linhas.extend(_linhas_loja_playwright(page, cert_key))
        finally:
            page.close()
    finally:
        if own_browser and browser:
            browser.close()
        if playwright_ctx:
            playwright_ctx.stop()

    return _dedupe_linhas(linhas)
