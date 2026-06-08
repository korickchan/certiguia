"""Busca de preços e-CPF A1/A3 nas certificadoras (Playwright)."""

import re
from datetime import datetime, timedelta

from certificado import CERTIFICADORAS, certificadoras_ativas, url_certificadora

CACHE_HORAS = 6
_cache: dict[str, dict] = {}

# Produtos que aparecem na mesma página e confundem o scraper
_OUTROS_PRODUTOS = ("e-cnpj", "e-pj", "safeid", "nf-e", "e-social", "e-cte", "e-mei")

_PRECO_MIN = {"A1": 90.0, "A3": 120.0}
_PRECO_MAX = 800.0

_CHROMIUM_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]


def _launch_chromium(playwright):
    """Chromium em Docker/Cloud Run exige --no-sandbox."""
    return playwright.chromium.launch(headless=True, args=_CHROMIUM_ARGS)


def _chave_cache(certificadora: str, produto_id: str) -> str:
    return f"{certificadora}:{produto_id}"


def _parse_valor_br(raw: str) -> float | None:
    raw = raw.strip().replace(" ", "")
    try:
        if "," in raw:
            valor = float(raw.replace(".", "").replace(",", "."))
        elif "." in raw and len(raw.split(".")[-1]) == 2:
            valor = float(raw)
        else:
            valor = float(raw)
        return valor
    except ValueError:
        return None


def _valor_ecpf_valido(valor: float | None, tipo: str) -> bool:
    if valor is None:
        return False
    return _PRECO_MIN.get(tipo, 120) <= valor <= _PRECO_MAX


def _bloco_produto(texto: str, chave_produto: str) -> str:
    """Recorta texto do card e-CPF A1/A3 até o próximo produto."""
    lower = texto.lower()
    idx = lower.find(chave_produto)
    if idx < 0:
        return ""

    resto = texto[idx:]
    fim = len(resto)
    for marcador in _OUTROS_PRODUTOS:
        pos = resto.lower().find(marcador, len(chave_produto))
        if pos > 0:
            fim = min(fim, pos)

    return resto[:fim]


_PRECO_MIN_PJ = {"A1": 200.0, "A3": 300.0}


def _valor_valido(valor: float | None, tipo: str, categoria: str = "pf") -> bool:
    if valor is None:
        return False
    limites = _PRECO_MIN_PJ if categoria == "pj" else _PRECO_MIN
    return limites.get(tipo, 120) <= valor <= _PRECO_MAX


def _preco_no_bloco(bloco: str, tipo: str, categoria: str = "pf") -> float | None:
    if not bloco:
        return None

    candidatos: list[float] = []

    m = re.search(
        r"a partir de\s*R\$\s*(\d{2,3}(?:[.\s]\d{3})*(?:,\d{2})?|\d{2,3})",
        bloco,
        re.IGNORECASE,
    )
    if m:
        valor = _parse_valor_br(m.group(1))
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)

    for m in re.finditer(r"R\$\s*(\d{2,3}(?:[.\s]\d{3})*(?:,\d{2})?|\d{2,3})", bloco, re.I):
        valor = _parse_valor_br(m.group(1))
        if not _valor_valido(valor, tipo, categoria):
            continue
        # Ignora parcelas (ex.: 12x R$ 15,58)
        if valor < 80:
            continue
        candidatos.append(valor)

    if not candidatos:
        return None
    return min(candidatos)


def _extrair_preco_produto(texto: str, chave_produto: str, tipo: str, categoria: str = "pf") -> float | None:
    """Localiza card do produto (ex.: e-cpf a1, e-cnpj a1) e lê preço."""
    for chave in [chave_produto, chave_produto.replace(" ", "")]:
        bloco = _bloco_produto(texto, chave)
        preco = _preco_no_bloco(bloco, tipo, categoria)
        if preco:
            return preco
    return None


def _extrair_preco_ecpf_texto(texto: str, tipo: str) -> float | None:
    return _extrair_preco_produto(texto, f"e-cpf {tipo.lower()}", tipo, "pf")


def _normalizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\u200b", ""))


def _familia_certificado(categoria: str) -> str:
    return "cpf" if categoria == "pf" else "cnpj"


def _extrair_preco_card_produto(
    texto: str, tipo: str, categoria: str = "pf", html: str = ""
) -> float | None:
    """Card «e-CPF/e-CNPJ A1/A3» com preço no mesmo bloco."""
    familia = _familia_certificado(categoria)
    fontes = [_normalizar_texto(texto)]
    if html:
        fontes.append(_normalizar_texto(re.sub(r"<[^>]+>", " ", html)))
    padroes = [
        rf"e-\s*{familia}\s*{tipo.lower()}\b.{{0,280}}?R\$\s*(\d{{2,3}}(?:\.\d{{3}})?,\d{{2}}|\d{{2,3}}(?:,\d{{2}})?)",
        rf"e-\s*{familia}\s*{tipo.lower()}\b.{{0,280}}?R\$\s*(\d{{2,3}})",
    ]
    for fonte in fontes:
        for pat in padroes:
            m = re.search(pat, fonte, re.I)
            if m:
                valor = _parse_valor_br(m.group(1))
                if _valor_valido(valor, tipo, categoria):
                    return valor
    return None


def _extrair_preco_card_ecpf(
    texto: str, tipo: str, categoria: str = "pf", html: str = ""
) -> float | None:
    return _extrair_preco_card_produto(texto, tipo, categoria, html)


def _extrair_preco_certclick(
    texto: str, html: str, tipo: str, categoria: str = "pf"
) -> float | None:
    """CertClick — cards na home; ordem fixa ou busca por rótulo e-CPF/e-CNPJ."""
    preco = _extrair_preco_card_produto(texto, tipo, categoria, html)
    if preco:
        return preco

    texto_norm = _normalizar_texto(texto)
    familia = _familia_certificado(categoria)
    for pat in (
        rf"e-\s*{familia}\s*\n?\s*{tipo.lower()}\b",
        rf"e-\s*{familia}\s*{tipo.lower()}\b",
    ):
        m = re.search(pat, texto_norm, re.I)
        if m:
            bloco = texto_norm[m.start() : m.start() + 280]
            preco = _preco_no_bloco(bloco, tipo, categoria)
            if preco:
                return preco

    # Ordem fixa na home: e-CNPJ A1, e-CNPJ A3, e-CPF A1, e-CPF A3
    vistos: list[float] = []
    for m in re.finditer(r"R\$\s*([\d.,]+)", texto_norm):
        valor = _parse_valor_br(m.group(1))
        if valor is None or not _valor_valido(valor, tipo, categoria):
            continue
        if valor not in vistos:
            vistos.append(valor)
    idx_map = {("pf", "A1"): 2, ("pf", "A3"): 3, ("pj", "A1"): 0, ("pj", "A3"): 1}
    idx = idx_map.get((categoria, tipo))
    if idx is not None and len(vistos) > idx:
        return vistos[idx]
    return None


def _extrair_preco_link_html(html: str, tipo: str, categoria: str = "pf") -> float | None:
    """Link — preços nos inputs radio (value), visível só para opção selecionada."""
    valores = []
    for m in re.finditer(r'id="product_\d+" value="([\d.]+)"', html):
        valor = _parse_valor_br(m.group(1))
        if _valor_valido(valor, tipo, categoria):
            valores.append(valor)
    if not valores:
        return None
    if tipo == "A1":
        faixa = [v for v in valores if 140 <= v <= 175]
        return min(faixa) if faixa else min(valores)
    faixa = [v for v in valores if 175 <= v <= 350]
    return min(faixa) if faixa else None


def _extrair_preco_soluti_ecpf(texto: str, html: str, tipo: str, categoria: str = "pf") -> float | None:
    """Soluti — página e-CPF com blocos CERTIFICADO/RENOVAÇÃO/KIT PF."""
    preco = _extrair_preco_soluti(html, tipo, categoria)
    if preco:
        return preco

    texto_norm = _normalizar_texto(texto)
    if tipo == "A1":
        rotulos = ("CERTIFICADO PF A1",)
    else:
        rotulos = (
            "RENOVAÇÃO CERTIFICADO PF A3",
            "RENOVACAO CERTIFICADO PF A3",
            "CERTIFICADO PF A3",
            "KIT PF A3",
        )
    for rotulo in rotulos:
        m = re.search(
            rf"{rotulo}.{{0,220}}?R\$\s*([\d.,]+)",
            texto_norm,
            re.I | re.S,
        )
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
    return None


SAFEWEB_CHECKOUT_URLS = {
    "pf": "https://www.safeweb.com.br/produtos/checkout/ecpf",
    "pj": "https://www.safeweb.com.br/produtos/checkout/ecnpj",
}
_safeweb_catalogo_cache: dict[str, list] = {}


def _scrape_safeweb_catalogo(categoria: str = "pf", timeout_ms: int = 45000, browser=None) -> list | None:
    """Carrega o checkout Safeweb e captura o catálogo JSON da API interna."""
    global _safeweb_catalogo_cache
    if categoria in _safeweb_catalogo_cache:
        return _safeweb_catalogo_cache[categoria]

    produtos: list | None = None
    checkout_url = SAFEWEB_CHECKOUT_URLS.get(categoria, SAFEWEB_CHECKOUT_URLS["pf"])

    def _capturar(page) -> list | None:
        captured: list | None = None

        def on_response(response):
            nonlocal captured
            if captured is not None:
                return
            if "GetListCatalogoProduto" not in response.url or not response.ok:
                return
            try:
                data = response.json()
            except Exception:
                return
            if isinstance(data, list) and data:
                captured = data

        page.on("response", on_response)
        page.goto(checkout_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(8000)
        return captured

    if browser is not None:
        page = browser.new_page()
        try:
            produtos = _capturar(page)
        finally:
            page.close()
    else:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            own_browser = _launch_chromium(p)
            try:
                page = own_browser.new_page()
                try:
                    produtos = _capturar(page)
                finally:
                    page.close()
            finally:
                own_browser.close()

    if produtos:
        _safeweb_catalogo_cache[categoria] = produtos
    return produtos


def _preco_safeweb_catalogo(produtos: list, tipo: str, categoria: str = "pf") -> float | None:
    """Filtra e-CPF/e-CNPJ, validade 1 ano, sem mídia física/acessório."""
    produto_tipo = "e-CPF" if categoria == "pf" else "e-CNPJ"
    candidatos: list[float] = []
    for item in produtos:
        if item.get("ProdutoTipo") != produto_tipo:
            continue
        if item.get("ProdutoModelo") != tipo:
            continue
        if item.get("Validade") != 1:
            continue
        if item.get("idAcessorio"):
            continue
        if item.get("idTipoUsoSafeId"):
            continue
        midia = item.get("MidiaTipo") or ""
        if tipo == "A1" and midia != "Arquivo":
            continue
        if tipo == "A3" and midia != "Sem mídia":
            continue
        valor = item.get("Valor")
        if valor is None:
            continue
        valor = float(valor)
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)
    if not candidatos:
        return None
    return min(candidatos)


def _extrair_preco_safeweb_catalogo(tipo: str, categoria: str = "pf", browser=None) -> float | None:
    produtos = _scrape_safeweb_catalogo(categoria, browser=browser)
    if not produtos:
        return None
    return _preco_safeweb_catalogo(produtos, tipo, categoria)


def _extrair_preco_serpro(texto: str, tipo: str, categoria: str = "pf") -> float | None:
    texto = _normalizar_texto(texto)
    familia = _familia_certificado(categoria)
    partes = re.split(rf"(?i)e-\s*{familia}", texto)
    for parte in partes[1:]:
        trecho = parte[:120].lower()
        if tipo.lower() not in trecho and f"a{tipo[-1]}" not in trecho:
            continue
        m = re.search(r"R\$\s*([\d.,]+)", parte)
        if m:
            valor = _parse_valor_br(m.group(1))
            if not _valor_valido(valor, tipo, categoria):
                continue
            if categoria == "pj":
                return valor
            if tipo == "A1" and 140 <= valor <= 200:
                return valor
            if tipo == "A3" and 200 <= valor <= 450:
                return valor

    candidatos = []
    for m in re.finditer(r"R\$\s*([\d.,]+)", texto):
        valor = _parse_valor_br(m.group(1))
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)
    if not candidatos:
        return None
    if categoria == "pj":
        return min(candidatos)
    if tipo == "A1":
        faixa = [v for v in candidatos if 140 <= v <= 200]
        return min(faixa) if faixa else None
    faixa = [v for v in candidatos if 200 <= v <= 450]
    return min(faixa) if faixa else None


def _extrair_preco_soluti(html: str, tipo: str, categoria: str = "pf") -> float | None:
    rotulos = []
    if categoria == "pj":
        rotulos = [f"CERTIFICADO PJ {tipo}", f"E-CNPJ {tipo}", f"e-CNPJ {tipo}"]
    else:
        rotulos = [f"CERTIFICADO PF {tipo}"]
    for produto in rotulos:
        m = re.search(
            rf"{produto}.{{0,500}}?R\$\s*([\d.,]+)",
            html,
            re.I | re.S,
        )
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
        m = re.search(
            rf'class="title">{produto}.*?</h2>.*?class="price"[^>]*>R\$\s*([\d.,]+)',
            html,
            re.I | re.S,
        )
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
    return None


def _extrair_preco_soluti_ecpf(texto: str, html: str, tipo: str, categoria: str = "pf") -> float | None:
    """Soluti — página e-CPF/e-CNPJ com blocos CERTIFICADO/RENOVAÇÃO/KIT."""
    preco = _extrair_preco_soluti(html, tipo, categoria)
    if preco:
        return preco

    texto_norm = _normalizar_texto(texto)
    if categoria == "pj":
        rotulos = (
            f"CERTIFICADO PJ {tipo}",
            f"E-CNPJ {tipo}",
            f"e-CNPJ {tipo}",
        )
    elif tipo == "A1":
        rotulos = ("CERTIFICADO PF A1",)
    else:
        rotulos = (
            "RENOVAÇÃO CERTIFICADO PF A3",
            "RENOVACAO CERTIFICADO PF A3",
            "CERTIFICADO PF A3",
            "KIT PF A3",
        )
    for rotulo in rotulos:
        m = re.search(
            rf"{rotulo}.{{0,220}}?R\$\s*([\d.,]+)",
            texto_norm,
            re.I | re.S,
        )
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
    return None


def _extrair_preco_link(texto: str, tipo: str, categoria: str = "pf") -> float | None:
    """Link — loja e-CPF/e-CNPJ, card «Sem Mídia A1/A3» ou token/cartão."""
    texto = _normalizar_texto(texto)
    if tipo == "A1":
        m = re.search(r"Sem\s*M[ií]dia\s*A1.*?R\$\s*([\d.,]+)", texto, re.I | re.S)
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
    else:
        for marcador in ("Token A3", "Cartão A3", "Cartao A3"):
            m = re.search(rf"{marcador}.{{0,200}}?R\$\s*([\d.,]+)", texto, re.I | re.S)
            if m:
                valor = _parse_valor_br(m.group(1))
                if _valor_valido(valor, tipo, categoria):
                    return valor
    familia = _familia_certificado(categoria)
    return _extrair_preco_produto(texto, f"e-{familia} {tipo.lower()}", tipo, categoria)


def _extrair_preco_online(texto: str, tipo: str, categoria: str = "pf") -> float | None:
    """Online Certificadora — card E-CPF/E-CNPJ A1/A3."""
    preco = _extrair_preco_card_produto(texto, tipo, categoria)
    if preco:
        return preco
    texto = _normalizar_texto(texto)
    familia = "CPF" if categoria == "pf" else "CNPJ"
    for pat in (
        rf"E-{familia}\s*{tipo}\b.{{0,160}}?R\$\s*([\d.,]+)",
        rf"E-{familia}\s*{tipo}\b.{{0,160}}?R\$([\d.,]+)",
        rf"E-{familia}\s*{tipo}\s*DE\s*1\s*ANO.{{0,80}}?R\$([\d.,]+)",
    ):
        m = re.search(pat, texto, re.I)
        if m:
            valor = _parse_valor_br(m.group(1))
            if _valor_valido(valor, tipo, categoria):
                return valor
    return None


def _extrair_preco_acdigital(page, tipo: str, categoria: str = "pf") -> float | None:
    """AC Digital — checkout eipar: seleciona e-PF A1/A3 e tipo de emissão."""

    def _disparar_change(seletor: str) -> None:
        page.evaluate(
            """(sel) => document.querySelector(sel)
            ?.dispatchEvent(new Event('change', {bubbles: true}))""",
            seletor,
        )

    def _selecionar_produto() -> bool:
        opcoes = page.evaluate(
            """() => Array.from(document.querySelectorAll('#form_PROProdutos_PROCodigos_1 option'))
            .map(o => ({v: o.value, t: o.textContent.trim()}))"""
        )
        alvo = None
        tipo_up = tipo.upper()
        if categoria == "pj":
            marcadores = (f"E-PJ {tipo_up}", f"E-CNPJ {tipo_up}", f"PESSOA JURÍDICA {tipo_up}", f"PJ {tipo_up}")
        else:
            marcadores = (f"E-PF {tipo_up}", f"E-CPF {tipo_up}", f"PESSOA FÍSICA {tipo_up}", f"PESSOA FISICA {tipo_up}")
        for opt in opcoes:
            texto = opt["t"].upper()
            if any(x in texto for x in ("CARTÃO", "CARTAO", "TOKEN", "LEITORA")):
                continue
            if "2 ANOS" in texto:
                continue
            if any(m in texto for m in marcadores):
                alvo = opt
                break
        if not alvo:
            return False
        page.select_option("#form_PROProdutos_PROCodigos_1", value=alvo["v"])
        _disparar_change("#form_PROProdutos_PROCodigos_1")
        return True

    def _selecionar_emissao() -> bool:
        page.wait_for_function(
            """() => {
                const sel = document.querySelector('select[name="TPETipoEmissao[1]"]');
                return sel && !sel.disabled && sel.options.length > 1;
            }""",
            timeout=25000,
        )
        emissoes = page.evaluate(
            """() => Array.from(document.querySelectorAll('select[name="TPETipoEmissao[1]"] option'))
            .filter(o => o.value)
            .map(o => ({v: o.value, t: o.textContent.trim()}))"""
        )
        if not emissoes:
            return False
        escolha = next(
            (o for o in emissoes if "presencial" in o["t"].lower()),
            emissoes[0],
        )
        page.select_option('select[name="TPETipoEmissao[1]"]', value=escolha["v"])
        _disparar_change('select[name="TPETipoEmissao[1]"]')
        return True

    def _ler_valor() -> float | None:
        for _ in range(25):
            bruto = page.input_value("#form_PROProdutos_VDPValor_1")
            valor = _parse_valor_br(re.sub(r"[^\d,.]", "", bruto))
            if valor and valor > 0 and _valor_valido(valor, tipo, categoria):
                return valor
            page.wait_for_timeout(400)
        return None

    try:
        comprar = page.locator("a[href*='eipar.com.br']").filter(has_text=re.compile(r"comprar", re.I))
        if comprar.count() == 0:
            comprar = page.locator("a:has-text('Comprar')")
        href = comprar.first.get_attribute("href")
        if not href:
            return None

        page.goto(href, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_selector("#form_PROProdutos_PROCodigos_1", timeout=30000)
        page.wait_for_timeout(2000)

        if not _selecionar_produto():
            return None
        page.wait_for_timeout(1000)

        if not _selecionar_emissao():
            return None
        page.wait_for_timeout(2000)

        return _ler_valor()
    except Exception:
        return None


def _scrape_pagina(
    certificadora_key: str,
    url: str,
    chave_produto: str,
    tipo: str,
    categoria: str = "pf",
    timeout_ms: int = 45000,
    browser=None,
) -> dict:
    nome_produto = chave_produto.upper()

    if certificadora_key == "safeweb":
        preco = _extrair_preco_safeweb_catalogo(tipo, categoria, browser=browser)
        if not preco:
            rotulo = "e-CPF" if categoria == "pf" else "e-CNPJ"
            return {
                "ok": False,
                "erro": f"Preço do {nome_produto} não detectado — confira manualmente no checkout Safeweb.",
            }
        rotulo = "e-CPF" if categoria == "pf" else "e-CNPJ"
        return {
            "ok": True,
            "preco": preco,
            "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "observacao": (
                f"Preço à vista do {nome_produto} (checkout Safeweb: {rotulo}, validade 1 ano, "
                f"{'arquivo' if tipo == 'A1' else 'sem mídia'}). Confira emissão no site antes de pagar."
            ),
        }

    wait_until = "domcontentloaded" if certificadora_key in (
        "valid", "certclick", "serpro", "soluti", "digitalsign", "link", "online", "acdigital",
    ) else "networkidle"
    wait_ms = 8000 if certificadora_key == "certisign" else 6000

    def _executar(page) -> tuple[float | None, str]:
        preco = None
        metodo = ""
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        page.wait_for_timeout(wait_ms)
        if certificadora_key == "certclick":
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
        html = page.content()
        texto = page.inner_text("body")

        if certificadora_key == "certisign":
            preco = _extrair_preco_certisign(html, tipo, categoria)
            if not preco:
                preco = _extrair_preco_produto(texto, chave_produto, tipo, categoria)
            metodo = f"preço à vista e-CPF {tipo} Certisign"

        elif certificadora_key == "certclick":
            preco = _extrair_preco_certclick(texto, html, tipo, categoria)
            metodo = "card e-CPF A1/A3 CertClick"

        elif certificadora_key == "serpro":
            preco = _extrair_preco_serpro(texto, tipo, categoria)
            metodo = "tabela Loja Serpro"

        elif certificadora_key == "soluti":
            preco = _extrair_preco_soluti_ecpf(texto, html, tipo, categoria)
            metodo = "página e-CPF Soluti (Certificado PF)"

        elif certificadora_key == "digitalsign":
            preco = _extrair_preco_card_ecpf(texto, tipo, categoria, html)
            metodo = "card e-CPF DigitalSign"

        elif certificadora_key == "link":
            preco = _extrair_preco_link_html(html, tipo, categoria)
            if not preco:
                preco = _extrair_preco_link(texto, tipo, categoria)
            metodo = "loja oficial Link (e-CPF PF)"

        elif certificadora_key == "online":
            preco = _extrair_preco_online(texto, tipo, categoria)
            if not preco:
                preco = _extrair_preco_card_ecpf(texto, tipo, categoria, html)
            metodo = "loja Online Certificadora"

        elif certificadora_key == "acdigital":
            preco = _extrair_preco_acdigital(page, tipo, categoria)
            rotulo = "e-PF" if categoria == "pf" else "e-PJ"
            metodo = f"checkout AC Digital ({rotulo} {tipo}, emissão presencial)"

        elif certificadora_key == "valid":
            preco = _extrair_preco_produto(texto, chave_produto, tipo, categoria)
            metodo = f"card {nome_produto} no site"

        if not preco:
            preco = _extrair_preco_produto(texto, chave_produto, tipo, categoria)
            if preco and certificadora_key == "serpro" and tipo == "A3" and preco < 200:
                preco = None
        return preco, metodo

    preco = None
    metodo = ""
    if browser is not None:
        page = browser.new_page()
        try:
            preco, metodo = _executar(page)
        finally:
            page.close()
    else:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            own_browser = _launch_chromium(p)
            try:
                page = own_browser.new_page()
                try:
                    preco, metodo = _executar(page)
                finally:
                    page.close()
            finally:
                own_browser.close()

    if not preco:
        return {
            "ok": False,
            "erro": f"Preço do {nome_produto} não detectado — confira manualmente no site.",
        }

    return {
        "ok": True,
        "preco": preco,
        "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "observacao": f"Preço à vista do {nome_produto} ({metodo}). Confira no checkout antes de pagar.",
    }


def _extrair_preco_certisign(html: str, tipo: str, categoria: str = "pf") -> float | None:
    """Certisign — lê regular_price do HTML (WooCommerce, entidades &quot;)."""
    candidatos: list[float] = []

    for m in re.finditer(
        r'regular_price(?:&quot;|"):(?:&quot;|")(\d{2,3}),(\d{2})(?:&quot;|")',
        html,
    ):
        valor = float(f"{m.group(1)}.{m.group(2)}")
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)

    # Fallback: preço à vista visível no HTML ("R$ 186,90")
    for m in re.finditer(
        r'(?:installment-value|heading-title|elementor-widget-container)[^>]*>R\$\s*(\d{2,3}),(\d{2})',
        html,
        re.I,
    ):
        valor = float(f"{m.group(1)}.{m.group(2)}")
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)

    for m in re.finditer(r'ou R\$\s*(\d{2,3}),(\d{2})\s*(?:&agrave;|à) vista', html, re.I):
        valor = float(f"{m.group(1)}.{m.group(2)}")
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)

    if not candidatos:
        return None

    unicos = sorted(set(candidatos))
    if tipo == "A1":
        piso = 200 if categoria == "pj" else 170
        teto = 350 if categoria == "pj" else 220
        faixa = [v for v in unicos if piso <= v <= teto]
        return faixa[0] if faixa else min(unicos)
    faixa = [v for v in unicos if 220 <= v <= 400]
    return faixa[0] if faixa else min(v for v in unicos if v >= 200)


def buscar_preco_produto(
    certificadora_key: str,
    produto_id: str,
    usar_cache: bool = True,
    browser=None,
) -> dict:
    from recomendacao import PRODUTOS

    produto = PRODUTOS.get(produto_id)
    if not produto:
        return {"certificadora": certificadora_key, "ok": False, "erro": "Produto inválido."}

    cert = CERTIFICADORAS.get(certificadora_key)
    if not cert or not cert.get("ativa", True):
        return {"certificadora": certificadora_key, "ok": False, "erro": "Certificadora indisponível."}

    tipo = produto["tipo_armazenamento"]
    chave = produto["chave_preco"]
    categoria = produto["categoria"]

    cache_key = _chave_cache(certificadora_key, produto_id)
    if usar_cache and cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.utcnow() - cached["atualizado_em"] < timedelta(hours=CACHE_HORAS):
            return cached["dados"]

    url = url_certificadora(certificadora_key, tipo, categoria)
    resultado = {
        "certificadora": certificadora_key,
        "nome": cert["nome"],
        "produto_id": produto_id,
        "tipo": produto["nome"],
        "url": url,
        "instrucao": cert.get(f"instrucao_{tipo.lower()}", ""),
        "atualizado_em": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
    }

    try:
        scrape = _scrape_pagina(certificadora_key, url, chave, tipo, categoria, browser=browser)
        resultado.update(scrape)
    except Exception as e:
        resultado.update({"ok": False, "erro": f"Falha ao acessar site: {str(e)[:120]}"})

    _cache[cache_key] = {"dados": resultado, "atualizado_em": datetime.utcnow()}
    return resultado


def buscar_preco_certificadora(
    certificadora_key: str,
    produto_id: str,
    usar_cache: bool = True,
) -> dict:
    return buscar_preco_produto(certificadora_key, produto_id, usar_cache)


def buscar_preco_por_tipo(certificadora_key: str, tipo: str, categoria: str = "pf", usar_cache: bool = True) -> dict:
    """Compatibilidade: busca por armazenamento A1/A3 e categoria pf/pj."""
    familia = "cpf" if categoria == "pf" else "cnpj"
    produto_id = f"e-{familia}-{tipo.lower()}"
    resultado = buscar_preco_produto(certificadora_key, produto_id, usar_cache)
    return resultado


def comparar_precos_produto(produto_id: str, usar_cache: bool = True) -> list[dict]:
    keys = list(certificadoras_ativas())
    resultados: list[dict] = []
    keys_scrape: list[str] = []

    for key in keys:
        if usar_cache:
            cache_key = _chave_cache(key, produto_id)
            if cache_key in _cache:
                cached = _cache[cache_key]
                if datetime.utcnow() - cached["atualizado_em"] < timedelta(hours=CACHE_HORAS):
                    resultados.append(cached["dados"])
                    continue
        keys_scrape.append(key)

    if keys_scrape:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = _launch_chromium(p)
                try:
                    for key in keys_scrape:
                        resultados.append(
                            buscar_preco_produto(key, produto_id, usar_cache=False, browser=browser)
                        )
                finally:
                    browser.close()
        except Exception as exc:
            msg = str(exc)[:120]
            for key in keys_scrape:
                cert = CERTIFICADORAS.get(key, {})
                resultados.append({
                    "certificadora": key,
                    "nome": cert.get("nome", key),
                    "produto_id": produto_id,
                    "ok": False,
                    "erro": f"Falha ao acessar site: {msg}",
                })

    com_preco = [r for r in resultados if r.get("ok")]
    if com_preco:
        menor = min(r["preco"] for r in com_preco)
        for r in resultados:
            r["melhor_preco"] = r.get("ok") and r["preco"] == menor
    else:
        for r in resultados:
            r["melhor_preco"] = False

    resultados.sort(key=lambda x: (not x.get("ok"), x.get("preco", 9999)))
    return resultados


def comparar_precos(produto_id: str, usar_cache: bool = True) -> list[dict]:
    """Compara preços para um produto (e-cpf-a1, e-cnpj-a3, etc.)."""
    return comparar_precos_produto(produto_id, usar_cache=usar_cache)


_playwright_ok: bool | None = None


def playwright_disponivel() -> bool:
    global _playwright_ok
    if _playwright_ok is not None:
        return _playwright_ok
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = _launch_chromium(p)
            browser.close()
        _playwright_ok = True
    except Exception:
        _playwright_ok = False
    return _playwright_ok
