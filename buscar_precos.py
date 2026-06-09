"""Busca de preços e-CPF A1/A3 nas certificadoras (HTTP rápido + Playwright quando necessário)."""

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from certificado import CERTIFICADORAS, certificadoras_ativas, url_certificadora

CACHE_HORAS = 6
_cache: dict[str, dict] = {}

# Produtos que aparecem na mesma página e confundem o scraper
_OUTROS_PRODUTOS = ("e-cnpj", "e-pj", "safeid", "nf-e", "e-social", "e-cte", "e-mei")

_PRECO_MIN = {"A1": 90.0, "A3": 120.0}
_PRECO_MAX = 800.0

_CHROMIUM_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
_HTTP_TIMEOUT = 28
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# SPA/API ou checkout com filtros JS — restante usa HTTP (segundos, não minutos)
_PLAYWRIGHT_ONLY = frozenset({"safeweb", "serpro", "acdigital"})

# Critérios padrão de busca de preço (checkout típico)
SCRAPE_EMISSAO = "Videoconferência"
SCRAPE_VALIDADE = "1 ano"
SAFEWEB_ID_EMISSAO_VIDEO = 3


def _texto_ascii_minusculo(valor: str) -> str:
    if not valor:
        return ""
    norm = unicodedata.normalize("NFKD", valor)
    return norm.encode("ascii", "ignore").decode().lower()


def _emissao_videoconferencia(item: dict) -> bool:
    if item.get("idTipoEmissao") == SAFEWEB_ID_EMISSAO_VIDEO:
        return True
    return "videoconfer" in _texto_ascii_minusculo(item.get("TipoEmissao") or "")


def _observacao_preco_padrao(nome_produto: str, metodo: str) -> str:
    return (
        f"Preço à vista — {nome_produto}, emissão {SCRAPE_EMISSAO.lower()}, "
        f"validade {SCRAPE_VALIDADE}. {metodo} Confira no checkout antes de pagar."
    )


def _launch_chromium(playwright):
    """Chromium em Docker/Cloud Run exige --no-sandbox."""
    return playwright.chromium.launch(headless=True, args=_CHROMIUM_ARGS)


def _fetch_html(url: str, timeout: int = _HTTP_TIMEOUT) -> str | None:
    """Baixa HTML estático — ~1s por site, sem Chromium."""
    try:
        import ssl
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )
        with urllib.request.urlopen(
            req, timeout=timeout, context=ssl.create_default_context()
        ) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _fetch_json(url: str, timeout: int = _HTTP_TIMEOUT) -> dict | list | None:
    raw = _fetch_html(url, timeout=timeout)
    if not raw:
        return None
    try:
        import json

        return json.loads(raw)
    except json.JSONDecodeError:
        return None


VALID_BASE = "https://validcertificadora.com.br"


def _valid_validade_anos(variant_title: str) -> int | None:
    t = _texto_ascii_minusculo(variant_title or "")
    if "6 mes" in t:
        return None
    if t in ("default title", "") or "1 ano" in t:
        return 1
    if "3 ano" in t:
        return 3
    if "2 ano" in t:
        return 2
    return None


def _valid_armazenamento(handle: str, title: str) -> str | None:
    h = _texto_ascii_minusculo(f"{handle} {title}")
    if "-a3" in h or " a3" in h or h.endswith("a3"):
        return "A3"
    if "-a1" in h or " a1" in h or h.endswith("a1"):
        return "A1"
    return None


def _valid_produto_tipo(handle: str, title: str) -> tuple[str, str] | None:
    h = _texto_ascii_minusculo(f"{handle} {title}")
    if "e-cnpj" in h:
        return "e-CNPJ", "pj"
    if "e-cpf" in h:
        return "e-CPF", "pf"
    return None


def _valid_midia_from_product(handle: str, title: str, arm: str) -> str:
    h = _texto_ascii_minusculo(f"{handle} {title}")
    if "nuvem" in h:
        return "nuvem"
    if "token" in h:
        return "token"
    if "cartao" in h or "cart" in h:
        return "cartao"
    if "sem-midia" in h or "sem midia" in h:
        return "sem_midia"
    return "arquivo" if arm == "A1" else "sem_midia"


def _valid_relevante(product: dict) -> bool:
    handle = product.get("handle") or ""
    title = product.get("title") or ""
    h = _texto_ascii_minusculo(handle)
    if any(x in h for x in ("combo", "-req", "copia", "leitora", "nf-e", "nfe", "ct-e", "cte", "safeid")):
        return False
    if "+" in title:
        return False
    return bool(_valid_produto_tipo(handle, title) and _valid_armazenamento(handle, title))


def _valid_handles_preco(tipo: str, categoria: str, midia: str | None = None) -> list[str]:
    fam = "cpf" if categoria == "pf" else "cnpj"
    base = f"e-{fam}-{tipo.lower()}"
    if tipo == "A1":
        return [base]
    if midia == "token":
        return [f"{base}-em-token"]
    if midia == "cartao":
        return [f"{base}-em-cartao"]
    if midia == "nuvem":
        return [f"{base}-em-nuvem", f"e-{fam}-a3-em-nuvem"]
    if midia == "sem_midia":
        return [base]
    return [f"{base}-em-token", base, f"{base}-em-cartao"]


def _valid_preco_de_produto(product: dict, validade_anos: int = 1) -> float | None:
    candidatos: list[float] = []
    variants = product.get("variants") or []
    for v in variants:
        va = _valid_validade_anos(v.get("title") or "")
        if va != validade_anos:
            continue
        try:
            candidatos.append(float(v["price"]))
        except (KeyError, TypeError, ValueError):
            continue
    if candidatos:
        return min(candidatos)
    if len(variants) == 1:
        try:
            return float(variants[0]["price"])
        except (KeyError, TypeError, ValueError):
            pass
    return None


def _valid_buscar_preco(
    tipo: str,
    categoria: str,
    validade_anos: int = 1,
    midia: str | None = None,
) -> tuple[float | None, str, str]:
    """Busca preço na API pública Shopify da Valid (/products/{handle}.json)."""
    for handle in _valid_handles_preco(tipo, categoria, midia):
        data = _fetch_json(f"{VALID_BASE}/products/{handle}.json")
        if not data or "product" not in data:
            continue
        product = data["product"]
        preco = _valid_preco_de_produto(product, validade_anos)
        if preco is not None and _valor_valido(preco, tipo, categoria):
            return preco, product.get("title", handle), f"{VALID_BASE}/products/{handle}"
    return None, "", ""


def _valid_all_products() -> list[dict]:
    """Todas as páginas do catálogo Shopify Valid."""
    todos: list[dict] = []
    pagina = 1
    while pagina <= 10:
        data = _fetch_json(f"{VALID_BASE}/collections/all/products.json?limit=250&page={pagina}")
        if not data or not isinstance(data, dict):
            break
        lote = data.get("products") or []
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < 250:
            break
        pagina += 1
    return todos


def valid_catalogo_itens() -> list[dict]:
    """Lista preços e-CPF/e-CNPJ da Valid (catálogo Shopify completo)."""
    rows: list[dict] = []
    for product in _valid_all_products():
        if not _valid_relevante(product):
            continue
        handle = product["handle"]
        title = product.get("title") or handle
        tip = _valid_produto_tipo(handle, title)
        if not tip:
            continue
        produto_tipo, categoria = tip
        arm = _valid_armazenamento(handle, title)
        if not arm:
            continue
        midia = _valid_midia_from_product(handle, title, arm)
        url = f"{VALID_BASE}/products/{handle}"
        emissao = "renovacao" if "renov" in _texto_ascii_minusculo(handle) else "videoconferencia"
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
            rows.append({
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
            })
    return rows


def _html_para_texto(html: str) -> str:
    t = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _resultado_preco_ok(preco: float, nome_produto: str, metodo: str) -> dict:
    return {
        "ok": True,
        "preco": preco,
        "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "observacao": _observacao_preco_padrao(nome_produto, f"({metodo})."),
    }


def _extrair_preco_html(
    certificadora_key: str,
    html: str,
    chave_produto: str,
    tipo: str,
    categoria: str = "pf",
) -> tuple[float | None, str]:
    """Extrai preço do HTML/texto — mesma lógica do Playwright, sem browser."""
    texto = _html_para_texto(html)
    nome_produto = chave_produto.upper()
    preco = None
    metodo = ""

    if certificadora_key == "certisign":
        preco = _extrair_preco_certisign(html, tipo, categoria)
        if not preco:
            preco = _extrair_preco_produto(texto, chave_produto, tipo, categoria)
        metodo = f"preço à vista e-CPF {tipo} Certisign (HTTP)"

    elif certificadora_key == "certclick":
        preco = _extrair_preco_certclick(texto, html, tipo, categoria)
        metodo = "card e-CPF A1/A3 CertClick (HTTP)"

    elif certificadora_key == "soluti":
        preco = _extrair_preco_soluti_ecpf(texto, html, tipo, categoria)
        metodo = "página e-CPF Soluti (HTTP)"

    elif certificadora_key == "digitalsign":
        preco = _extrair_preco_card_ecpf(texto, tipo, categoria, html)
        metodo = "card e-CPF DigitalSign (HTTP)"

    elif certificadora_key == "link":
        preco = _extrair_preco_link_html(html, tipo, categoria)
        if not preco:
            preco = _extrair_preco_link(texto, tipo, categoria)
        metodo = "loja oficial Link (HTTP)"

    elif certificadora_key == "online":
        preco = _extrair_preco_online(texto, tipo, categoria)
        if not preco:
            preco = _extrair_preco_card_ecpf(texto, tipo, categoria, html)
        metodo = "loja Online Certificadora (HTTP)"

    elif certificadora_key == "valid":
        preco, titulo, _url = _valid_buscar_preco(tipo, categoria)
        if not preco:
            preco = _extrair_preco_valid_html(html, tipo, categoria)
            metodo = "catálogo Valid (HTML Shopify)"
        else:
            metodo = f"Valid Shopify API ({titulo})"

    if not preco:
        preco = _extrair_preco_produto(texto, chave_produto, tipo, categoria)
    return preco, metodo


def _scrape_http(
    certificadora_key: str,
    url: str,
    chave_produto: str,
    tipo: str,
    categoria: str = "pf",
) -> dict | None:
    if certificadora_key == "valid":
        preco, titulo, product_url = _valid_buscar_preco(tipo, categoria)
        if not preco:
            html = _fetch_html(url)
            if html:
                preco = _extrair_preco_valid_html(html, tipo, categoria)
                titulo = chave_produto
                product_url = url
        if not preco:
            return None
        resultado = _resultado_preco_ok(preco, chave_produto.upper(), f"Valid Shopify ({titulo})")
        resultado["url"] = product_url
        return resultado

    html = _fetch_html(url)
    if not html:
        return None
    preco, metodo = _extrair_preco_html(
        certificadora_key, html, chave_produto, tipo, categoria
    )
    if not preco:
        return None
    return _resultado_preco_ok(preco, chave_produto.upper(), metodo)


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


def _extrair_preco_valid_html(html: str, tipo: str, categoria: str) -> float | None:
    """Fallback: preços em centavos no JSON embutido da busca Shopify."""
    fam = "cpf" if categoria == "pf" else "cnpj"
    alvo = f"e-{fam}-{tipo.lower()}"
    candidatos: list[float] = []
    for m in re.finditer(
        rf'"handle":"({re.escape(alvo)}[^"]*)"[^}}]{{0,500}}?"price":(\d+)',
        html,
        re.I,
    ):
        handle, cents = m.group(1), int(m.group(2))
        if "combo" in handle or "leitora" in handle:
            continue
        valor = cents / 100.0
        if _valor_valido(valor, tipo, categoria):
            candidatos.append(valor)
    return min(candidatos) if candidatos else None


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
SAFEWEB_CATALOGO_MIN_ITENS = 15
_safeweb_catalogo_cache: dict[str, list] = {}


def _safeweb_melhor_catalogo(capturados: list[list]) -> list | None:
    if not capturados:
        return None
    return max(capturados, key=len)


def _safeweb_bloquear_peso(route) -> None:
    if route.request.resource_type in ("image", "font", "media"):
        route.abort()
    else:
        route.continue_()


def _scrape_safeweb_catalogo(categoria: str = "pf", timeout_ms: int = 55000, browser=None) -> list | None:
    """Carrega checkout Safeweb e captura catálogo JSON (API interna)."""
    global _safeweb_catalogo_cache
    cached = _safeweb_catalogo_cache.get(categoria)
    if cached and len(cached) >= SAFEWEB_CATALOGO_MIN_ITENS:
        return cached

    checkout_url = SAFEWEB_CHECKOUT_URLS.get(categoria, SAFEWEB_CHECKOUT_URLS["pf"])

    def _capturar(page) -> list | None:
        lotes: list[list] = []

        def on_response(response):
            if "GetListCatalogoProduto" not in response.url or not response.ok:
                return
            try:
                data = response.json()
            except Exception:
                return
            if isinstance(data, list) and data:
                lotes.append(data)

        page.route("**/*", _safeweb_bloquear_peso)
        page.on("response", on_response)

        for tentativa in range(2):
            lotes.clear()
            try:
                with page.expect_response(
                    lambda r: "GetListCatalogoProduto" in r.url and r.ok,
                    timeout=timeout_ms,
                ):
                    page.goto(checkout_url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception:
                page.goto(checkout_url, wait_until="domcontentloaded", timeout=timeout_ms)

            for _ in range(24):
                melhor = _safeweb_melhor_catalogo(lotes)
                if melhor and len(melhor) >= SAFEWEB_CATALOGO_MIN_ITENS:
                    return melhor
                page.wait_for_timeout(500)

            if tentativa == 0:
                page.wait_for_timeout(1500)

        return None

    produtos: list | None = None
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

    if produtos and len(produtos) >= SAFEWEB_CATALOGO_MIN_ITENS:
        _safeweb_catalogo_cache[categoria] = produtos
        return produtos
    return None


def _preco_safeweb_catalogo(produtos: list, tipo: str, categoria: str = "pf") -> float | None:
    """Filtra e-CPF/e-CNPJ, videoconferência, validade 1 ano, mídia correta A1/A3."""
    produto_tipo = "e-CPF" if categoria == "pf" else "e-CNPJ"
    candidatos_video: list[float] = []
    candidatos_outros: list[float] = []

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
        if tipo == "A3" and midia not in ("Sem mídia", "Cartão", "Token"):
            continue
        valor = item.get("Valor")
        if valor is None:
            continue
        valor = float(valor)
        if not _valor_valido(valor, tipo, categoria):
            continue
        if _emissao_videoconferencia(item):
            candidatos_video.append(valor)
        else:
            candidatos_outros.append(valor)

    pool = candidatos_video or candidatos_outros
    if not pool:
        return None
    return min(pool)


def _extrair_preco_safeweb_catalogo(tipo: str, categoria: str = "pf", browser=None) -> float | None:
    produtos = _scrape_safeweb_catalogo(categoria, browser=browser)
    if not produtos:
        return None
    return _preco_safeweb_catalogo(produtos, tipo, categoria)


def _scrape_safeweb_pagina(
    tipo: str,
    categoria: str,
    browser=None,
    nome_produto: str = "",
) -> dict:
    """Busca Safeweb com catálogo API — roda em página dedicada (mais estável no Render)."""
    rotulo = nome_produto or f"E-{'CPF' if categoria == 'pf' else 'CNPJ'} {tipo}"
    preco = _extrair_preco_safeweb_catalogo(tipo, categoria, browser=browser)
    if preco is None:
        return {
            "ok": False,
            "erro": (
                f"Preço do {rotulo} não detectado no Safeweb "
                f"(videoconferência + 1 ano). Catálogo incompleto ou indisponível."
            ),
        }
    rotulo_prod = "e-CPF" if categoria == "pf" else "e-CNPJ"
    return {
        "ok": True,
        "preco": preco,
        "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "observacao": _observacao_preco_padrao(
            rotulo,
            f"Safeweb checkout ({rotulo_prod}, mídia {'arquivo' if tipo == 'A1' else 'sem mídia/token'}).",
        ),
    }


SERPRO_LOJA_URL = "https://servicos.serpro.gov.br/loja/certificacao-digital/"

SERPRO_FILTROS = {"pf": "Pessoa Física", "pj": "Pessoa Jurídica"}
SERPRO_MIDIA = {"A1": "Arquivo", "A3": "Somente o Certificado"}


def _serpro_desmarcar_filtros(page) -> None:
    for label in (
        "Bancos",
        "Pessoa Física",
        "Pessoa Jurídica",
        "Adm Pública Direta",
        "Adm Pública Indireta",
        "Arquivo",
        "Nuvem",
        "Somente o Certificado",
        "1 ano",
        "2 anos",
    ):
        try:
            loc = page.get_by_label(label, exact=True)
            if loc.count() and loc.first.is_checked():
                loc.first.uncheck()
        except Exception:
            pass
    page.wait_for_timeout(400)


def _serpro_aplicar_filtros(page, categoria: str, tipo: str, validade: str) -> None:
    _serpro_desmarcar_filtros(page)
    for label in (SERPRO_FILTROS[categoria], SERPRO_MIDIA[tipo.upper()], validade):
        page.get_by_label(label, exact=True).check()
    page.wait_for_timeout(1200)


def _serpro_ler_preco_card(page, categoria: str, tipo: str) -> float | None:
    familia = "e-CPF" if categoria == "pf" else "e-CNPJ"
    texto = _normalizar_texto(page.inner_text("body"))
    padrao = (
        rf"{familia}\s*\|\s*{tipo}\s*-\s*\d+\s*ano[s]?"
        rf"[\s\S]{{0,220}}?"
        rf"R\$\s*([\d.,]+)"
    )
    m = re.search(padrao, texto, re.I)
    if not m:
        return None
    valor = _parse_valor_br(m.group(1))
    if _valor_valido(valor, tipo, categoria):
        return valor
    return None


def _extrair_preco_serpro_loja(page, tipo: str, categoria: str = "pf") -> tuple[float | None, str]:
    """Marca filtros na loja Serpro e lê o card e-CPF/e-CNPJ."""
    tipo = tipo.upper()
    page.goto(SERPRO_LOJA_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)

    _serpro_aplicar_filtros(page, categoria, tipo, "1 ano")
    preco = _serpro_ler_preco_card(page, categoria, tipo)
    if preco is not None:
        return preco, "1 ano"

    if tipo == "A3":
        _serpro_aplicar_filtros(page, categoria, tipo, "2 anos")
        preco = _serpro_ler_preco_card(page, categoria, tipo)
        if preco is not None:
            return preco, "2 anos (Serpro não lista A3 com 1 ano)"

    return None, "1 ano"


def _scrape_serpro_pagina(
    tipo: str,
    categoria: str,
    browser=None,
    nome_produto: str = "",
) -> dict:
    rotulo = nome_produto or f"E-{'CPF' if categoria == 'pf' else 'CNPJ'} {tipo}"

    def _run(page) -> dict:
        preco, validade_label = _extrair_preco_serpro_loja(page, tipo, categoria)
        if preco is None:
            return {
                "ok": False,
                "erro": (
                    f"Preço do {rotulo} não encontrado na loja Serpro "
                    f"(marque: {SERPRO_FILTROS[categoria]}, {SERPRO_MIDIA[tipo.upper()]}, 1 ano)."
                ),
            }
        obs_extra = f" Validade na loja: {validade_label}." if "2 anos" in validade_label else ""
        return {
            "ok": True,
            "preco": preco,
            "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "observacao": _observacao_preco_padrao(
                rotulo,
                f"Loja Serpro ({SERPRO_FILTROS[categoria]} + {SERPRO_MIDIA[tipo.upper()]} + {validade_label}).",
            )
            + obs_extra,
        }

    if browser is not None:
        page = browser.new_page()
        try:
            return _run(page)
        finally:
            page.close()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        own = _launch_chromium(p)
        try:
            page = own.new_page()
            try:
                return _run(page)
            finally:
                page.close()
        finally:
            own.close()


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
        return _scrape_safeweb_pagina(tipo, categoria, browser=browser, nome_produto=nome_produto)

    if certificadora_key == "serpro":
        return _scrape_serpro_pagina(tipo, categoria, browser=browser, nome_produto=nome_produto)

    wait_until = "domcontentloaded" if certificadora_key in (
        "valid", "certclick", "soluti", "digitalsign", "link", "online", "acdigital",
    ) else "networkidle"
    wait_ms = 8000 if certificadora_key == "certisign" else 6000

    def _executar(page) -> tuple[float | None, str]:
        if certificadora_key == "acdigital":
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            page.wait_for_timeout(wait_ms)
            preco = _extrair_preco_acdigital(page, tipo, categoria)
            rotulo = "e-PF" if categoria == "pf" else "e-PJ"
            metodo = f"checkout AC Digital ({rotulo} {tipo}, emissão presencial)"
            return preco, metodo

        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        page.wait_for_timeout(wait_ms)
        if certificadora_key == "certclick":
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
        html = page.content()
        preco, metodo = _extrair_preco_html(
            certificadora_key, html, chave_produto, tipo, categoria
        )
        if metodo and "(HTTP)" in metodo:
            metodo = metodo.replace(" (HTTP)", "")
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

    return _resultado_preco_ok(preco, nome_produto, metodo)


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
    prefer_http: bool = True,
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
        scrape = None
        if prefer_http and certificadora_key not in _PLAYWRIGHT_ONLY:
            scrape = _scrape_http(certificadora_key, url, chave, tipo, categoria)
            if scrape and scrape.get("ok"):
                resultado.update(scrape)
            else:
                resultado.update({
                    "ok": False,
                    "erro": f"Preço do {produto['nome']} não detectado via HTTP — tentando browser.",
                })
        else:
            scrape = _scrape_pagina(
                certificadora_key, url, chave, tipo, categoria, browser=browser
            )
            resultado.update(scrape)
    except Exception as e:
        resultado.update({"ok": False, "erro": f"Falha ao acessar site: {str(e)[:120]}"})

    if resultado.get("ok"):
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


def _ordem_scrape_certificadoras(keys: list[str]) -> list[str]:
    """Safeweb/Serpro primeiro — dependem de API/filtros e falham se o browser estiver sob carga."""
    prioridade = ("safeweb", "serpro")
    return [k for k in prioridade if k in keys] + [k for k in keys if k not in prioridade]


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

    if not keys_scrape:
        pass
    else:
        http_keys = [k for k in keys_scrape if k not in _PLAYWRIGHT_ONLY]
        pw_keys = [k for k in keys_scrape if k in _PLAYWRIGHT_ONLY]
        por_key: dict[str, dict] = {}

        if "safeweb" in pw_keys:
            try:
                por_key["safeweb"] = buscar_preco_produto(
                    "safeweb", produto_id, usar_cache=False, browser=None, prefer_http=False
                )
            except Exception as exc:
                cert = CERTIFICADORAS.get("safeweb", {})
                por_key["safeweb"] = {
                    "certificadora": "safeweb",
                    "nome": cert.get("nome", "Safeweb"),
                    "produto_id": produto_id,
                    "ok": False,
                    "erro": f"Falha ao acessar site: {str(exc)[:120]}",
                }
            pw_keys = [k for k in pw_keys if k != "safeweb"]

        if http_keys:
            with ThreadPoolExecutor(max_workers=min(8, len(http_keys))) as pool:
                futuros = {
                    pool.submit(
                        buscar_preco_produto,
                        key,
                        produto_id,
                        False,
                        None,
                        True,
                    ): key
                    for key in http_keys
                }
                for fut in as_completed(futuros):
                    key = futuros[fut]
                    try:
                        por_key[key] = fut.result()
                    except Exception as exc:
                        cert = CERTIFICADORAS.get(key, {})
                        por_key[key] = {
                            "certificadora": key,
                            "nome": cert.get("nome", key),
                            "produto_id": produto_id,
                            "ok": False,
                            "erro": str(exc)[:120],
                        }
                    if not por_key[key].get("ok"):
                        if key not in _PLAYWRIGHT_ONLY:
                            pw_keys.append(key)

        pw_keys = _ordem_scrape_certificadoras(list(dict.fromkeys(pw_keys)))

        if pw_keys:
            try:
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = _launch_chromium(p)
                    try:
                        for key in pw_keys:
                            por_key[key] = buscar_preco_produto(
                                key,
                                produto_id,
                                usar_cache=False,
                                browser=browser,
                                prefer_http=False,
                            )
                    finally:
                        browser.close()
            except Exception as exc:
                msg = str(exc)[:120]
                for key in pw_keys:
                    if key not in por_key or por_key[key].get("ok"):
                        continue
                    cert = CERTIFICADORAS.get(key, {})
                    por_key[key] = {
                        "certificadora": key,
                        "nome": cert.get("nome", key),
                        "produto_id": produto_id,
                        "ok": False,
                        "erro": f"Falha ao acessar site: {msg}",
                    }

        resultados.extend(por_key[k] for k in keys_scrape if k in por_key)

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
