"""Catálogo centralizado de preços — varredura periódica e consulta instantânea."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from certificado import CERTIFICADORAS, certificadoras_ativas, url_certificadora
from recomendacao import PRODUTOS

CATALOGO_HORAS = int(os.getenv("CATALOGO_PRECOS_HORAS", "168"))  # padrão: 1 semana

OPCOES_EMISSAO = [
    ("videoconferencia", "Videoconferência (online)"),
    ("presencial", "Presencial (unidade da certificadora)"),
]
OPCOES_MIDIA_A1 = [
    ("arquivo", "Arquivo no computador"),
    ("nuvem", "Nuvem (HSM)"),
]
OPCOES_MIDIA_A3 = [
    ("token", "Token USB / pendrive"),
    ("cartao", "Cartão inteligente"),
    ("sem_midia", "Sem mídia física"),
]
OPCOES_VALIDADE = [1, 2, 3]

MIDIAS_VALIDAS = {m[0] for m in OPCOES_MIDIA_A1} | {m[0] for m in OPCOES_MIDIA_A3}
EMISSOES_VALIDAS = {e[0] for e in OPCOES_EMISSAO}

AJUDA_PREFERENCIAS_INTRO = (
    "Cada certificadora cobra valores diferentes conforme como você emite, "
    "por quanto tempo vale e onde o certificado fica guardado. "
    "Escolha o que combina com sua rotina — usamos isso para mostrar preços reais."
)

AJUDA_EMISSAO = {
    "videoconferencia": (
        "Identificação por videochamada, de casa ou do consultório, com documentos em mãos. "
        "É a forma mais prática para a maioria das pessoas e, em muitas certificadoras, "
        "tem preço menor que ir presencialmente."
    ),
    "presencial": (
        "Você comparece a uma unidade da certificadora (loja ou ponto credenciado) "
        "com documentos originais. Indicado se preferir atendimento presencial, "
        "se a certificadora não oferecer videoconferência para o seu caso, "
        "ou quando exigirem validação física."
    ),
}

AJUDA_MIDIA_A1 = {
    "arquivo": (
        "O certificado é instalado como arquivo digital (.pfx) em um único computador. "
        "É o formato mais comum de A1 e, em geral, o mais barato. "
        "Ideal se você usa sempre o mesmo PC ou notebook."
    ),
    "nuvem": (
        "O certificado fica em servidores seguros da certificadora (HSM/nuvem), "
        "não no seu computador. Você acessa pela internet, de qualquer lugar. "
        "Útil para clínica com vários profissionais, e-CNPJ da empresa ou "
        "quem não quer depender de um PC específico."
    ),
}

AJUDA_MIDIA_A3 = {
    "token": (
        "Dispositivo USB (token ou pendrive criptográfico) que você conecta no computador "
        "para assinar documentos. Pode usar em vários PCs — basta levar o token com você. "
        "É a opção mais comum de A3."
    ),
    "cartao": (
        "Cartão inteligente (smart card) usado com leitora conectada ao computador. "
        "Funciona como o token, mas no formato cartão. Algumas certificadoras "
        "oferecem só cartão ou só token — o preço pode variar."
    ),
    "sem_midia": (
        "Emissão ou renovação sem entrega de token/cartão novo — o certificado "
        "continua no dispositivo que você já tem, ou em formato digital, "
        "conforme a certificadora. Nem sempre está disponível; costuma aparecer "
        "em renovações."
    ),
}

AJUDA_VALIDADE = (
    "Tempo em que o certificado vale antes de precisar renovar. "
    "1 ano é o mais ofertado e, em geral, tem o menor valor inicial. "
    "Validades de 2 ou 3 anos podem sair mais caras no total, "
    "mas evitam renovar todo ano."
)

AJUDA_SECAO_A1 = (
    "Certificado A1 — fica no computador (arquivo) ou na nuvem. "
    "Indicado quando você usa essencialmente um único equipamento."
)

AJUDA_SECAO_A3 = (
    "Certificado A3 — fica em token USB, cartão ou equivalente. "
    "Indicado para usar em vários computadores ou quando a recomendação "
    "do sistema exige mídia física."
)

AJUDA_VARIOS_COMPUTADORES = (
    "Um só PC → em geral recomendamos A1 (arquivo ou nuvem), que costuma ser mais barato. "
    "Vários PCs → A3 com token ou cartão: você conecta o dispositivo em cada computador "
    "em que for assinar documentos."
)

_varredura_lock = threading.Lock()
_varredura_status: dict = {"running": False, "erro": None, "itens": 0}


@dataclass
class FiltroPreco:
    produto_id: str
    categoria: str
    armazenamento: str
    emissao: str = "videoconferencia"
    validade_anos: int = 1
    midia: str | None = None

    @property
    def produto_tipo(self) -> str:
        return "e-CPF" if self.categoria == "pf" else "e-CNPJ"

    def rotulo(self) -> str:
        midia_map = dict(OPCOES_MIDIA_A1 + OPCOES_MIDIA_A3)
        emissao_map = dict(OPCOES_EMISSAO)
        midia = midia_map.get(self.midia or "", self.midia or "padrão")
        emissao = emissao_map.get(self.emissao or "", self.emissao or "—")
        return (
            f"{self.produto_tipo} {self.armazenamento} · {emissao} · "
            f"{self.validade_anos} ano(s) · {midia}"
        )


def _normalizar_midia(valor: str | None) -> str:
    if not valor:
        return ""
    v = valor.lower().strip()
    if "nuvem" in v or v == "cloud":
        return "nuvem"
    if "arquivo" in v:
        return "arquivo"
    if "pend" in v or "usb" in v:
        return "token"
    if "token" in v:
        return "token"
    if "cart" in v:
        return "cartao"
    if "sem" in v and "m" in v:
        return "sem_midia"
    return v


def _normalizar_emissao(item: dict | None = None, texto: str | None = None) -> str:
    if item:
        from buscar_precos import _emissao_videoconferencia

        if _emissao_videoconferencia(item):
            return "videoconferencia"
        t = (item.get("TipoEmissao") or "").lower()
        if "video" in t:
            return "videoconferencia"
        if "presen" in t:
            return "presencial"
        return "outro"
    if texto and "video" in texto.lower():
        return "videoconferencia"
    return "videoconferencia"


def filtros_de_produto(
    produto_id: str,
    *,
    midia: str | None = None,
    emissao: str = "videoconferencia",
    validade_anos: int = 1,
) -> FiltroPreco:
    produto = PRODUTOS[produto_id]
    arm = produto["tipo_armazenamento"]
    if not midia:
        midia = "arquivo" if arm == "A1" else "token"
    return FiltroPreco(
        produto_id=produto_id,
        categoria=produto["categoria"],
        armazenamento=arm,
        emissao=emissao,
        validade_anos=validade_anos,
        midia=_normalizar_midia(midia),
    )


def ajustar_preferencias_vet(vet) -> None:
    """Garante mídia compatível com A1/A3 do produto recomendado."""
    from recomendacao import produto_id_efetivo

    arm = PRODUTOS[produto_id_efetivo(vet)]["tipo_armazenamento"]
    opcoes = OPCOES_MIDIA_A3 if arm == "A3" else OPCOES_MIDIA_A1
    valid = {o[0] for o in opcoes}
    if vet.preferencia_midia not in valid:
        vet.preferencia_midia = opcoes[0][0]
    if vet.preferencia_emissao not in EMISSOES_VALIDAS:
        vet.preferencia_emissao = "videoconferencia"
    if (vet.preferencia_validade_anos or 1) not in OPCOES_VALIDADE:
        vet.preferencia_validade_anos = 1


def filtros_de_vet(vet) -> FiltroPreco:
    from recomendacao import produto_id_efetivo

    ajustar_preferencias_vet(vet)
    pid = produto_id_efetivo(vet)
    midia = getattr(vet, "preferencia_midia", None) or None
    emissao = getattr(vet, "preferencia_emissao", None) or "videoconferencia"
    validade = getattr(vet, "preferencia_validade_anos", None) or 1
    return filtros_de_produto(pid, midia=midia, emissao=emissao, validade_anos=int(validade or 1))


def _chave_catalogo(
    certificadora: str,
    produto_tipo: str,
    armazenamento: str,
    categoria: str,
    midia: str,
    emissao: str,
    validade_anos: int,
) -> str:
    return "|".join(
        [
            certificadora,
            produto_tipo,
            armazenamento,
            categoria,
            midia or "-",
            emissao or "-",
            str(validade_anos),
        ]
    )


def _formatar_preco(preco: float) -> str:
    return f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def init_catalogo(db, PrecoCatalogo, CatalogoMeta):
    """Registra modelos no módulo (evita import circular)."""
    global _PrecoCatalogo, _CatalogoMeta, _db
    _PrecoCatalogo = PrecoCatalogo
    _CatalogoMeta = CatalogoMeta
    _db = db


_PrecoCatalogo = None
_CatalogoMeta = None
_db = None


def _upsert_preco(
    *,
    certificadora: str,
    produto_tipo: str,
    categoria: str,
    armazenamento: str,
    midia: str,
    emissao: str,
    validade_anos: int,
    preco: float,
    url: str = "",
    observacao: str = "",
    fonte: str = "varredura",
) -> None:
    chave = _chave_catalogo(
        certificadora, produto_tipo, armazenamento, categoria, midia, emissao, validade_anos
    )
    row = _PrecoCatalogo.query.filter_by(chave=chave).first()
    if not row:
        row = _PrecoCatalogo(chave=chave, certificadora=certificadora)
        _db.session.add(row)
    row.produto_tipo = produto_tipo
    row.categoria = categoria
    row.armazenamento = armazenamento
    row.midia = midia
    row.emissao = emissao
    row.validade_anos = validade_anos
    row.preco = preco
    row.url = url
    row.observacao = observacao
    row.fonte = fonte
    row.atualizado_em = datetime.utcnow()


def importar_itens_safeweb(produtos: list, categoria: str) -> int:
    from buscar_precos import _valor_valido

    n = 0
    cat = categoria
    url_base = url_certificadora("safeweb", "A1", cat)
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
        if not _valor_valido(valor, modelo, cat):
            continue
        validade = int(item.get("Validade") or 1)
        midia = _normalizar_midia(item.get("MidiaTipo"))
        emissao = _normalizar_emissao(item=item)
        _upsert_preco(
            certificadora="safeweb",
            produto_tipo=produto_tipo,
            categoria=cat,
            armazenamento=modelo,
            midia=midia,
            emissao=emissao,
            validade_anos=validade,
            preco=valor,
            url=url_base,
            observacao=f"Safeweb — {produto_tipo} {modelo}, {item.get('MidiaTipo') or '—'}, "
            f"{item.get('TipoEmissao') or '—'}, {validade} ano(s).",
            fonte="safeweb_api",
        )
        n += 1
    return n


def _salvar_resultado_scrape(produto_id: str, resultado: dict) -> None:
    if not resultado.get("ok"):
        return
    produto = PRODUTOS[produto_id]
    filtros = filtros_de_produto(produto_id)
    _upsert_preco(
        certificadora=resultado["certificadora"],
        produto_tipo=filtros.produto_tipo,
        categoria=filtros.categoria,
        armazenamento=filtros.armazenamento,
        midia=filtros.midia or "",
        emissao=filtros.emissao,
        validade_anos=filtros.validade_anos,
        preco=float(resultado["preco"]),
        url=resultado.get("url") or "",
        observacao=resultado.get("observacao") or "",
        fonte="varredura",
    )


def _executar_varredura() -> None:
    from buscar_precos import _scrape_safeweb_catalogo, comparar_precos_produto

    with _varredura_lock:
        _varredura_status.update({"running": True, "erro": None, "itens": 0})

    meta = _CatalogoMeta.query.first()
    if not meta:
        meta = _CatalogoMeta()
        _db.session.add(meta)
    meta.status = "running"
    meta.iniciado_em = datetime.utcnow()
    meta.erro = None
    _db.session.commit()

    total = 0
    try:
        for produto_id in PRODUTOS:
            resultados = comparar_precos_produto(produto_id, usar_cache=False)
            for r in resultados:
                _salvar_resultado_scrape(produto_id, r)
                if r.get("ok"):
                    total += 1
            _db.session.commit()

        for categoria in ("pf", "pj"):
            produtos = _scrape_safeweb_catalogo(categoria, browser=None)
            if produtos:
                total += importar_itens_safeweb(produtos, categoria)
            _db.session.commit()

        meta.status = "ok"
        meta.concluido_em = datetime.utcnow()
        meta.itens_total = _PrecoCatalogo.query.count()
        meta.erro = None
        _db.session.commit()
        with _varredura_lock:
            _varredura_status.update({"running": False, "itens": total, "erro": None})
    except Exception as exc:
        _db.session.rollback()
        meta.status = "error"
        meta.erro = str(exc)[:500]
        _db.session.commit()
        with _varredura_lock:
            _varredura_status.update({"running": False, "erro": str(exc)[:200]})


def iniciar_varredura_background(app) -> bool:
    with _varredura_lock:
        if _varredura_status.get("running"):
            return False

    def _run():
        with app.app_context():
            _executar_varredura()

    threading.Thread(target=_run, daemon=True).start()
    return True


def catalogo_precisa_atualizar() -> bool:
    meta = _CatalogoMeta.query.first()
    if not meta or not meta.concluido_em:
        return _PrecoCatalogo.query.count() == 0
    return datetime.utcnow() - meta.concluido_em > timedelta(hours=CATALOGO_HORAS)


def info_catalogo() -> dict:
    meta = _CatalogoMeta.query.first()
    with _varredura_lock:
        running = _varredura_status.get("running", False)
    total = _PrecoCatalogo.query.count()
    concluido = meta.concluido_em if meta else None
    return {
        "total_itens": total,
        "ultima_varredura": concluido,
        "precisa_atualizar": catalogo_precisa_atualizar(),
        "varredura_em_andamento": running,
        "status": meta.status if meta else "vazio",
        "intervalo_horas": CATALOGO_HORAS,
        "intervalo_dias": round(CATALOGO_HORAS / 24, 1),
    }


def _emissao_compativel(filtro: FiltroPreco, emissao_row: str) -> bool:
    e = (emissao_row or "").lower()
    if filtro.emissao == "videoconferencia":
        return e in ("videoconferencia", "video", "")
    if filtro.emissao == "presencial":
        return e in ("presencial",)
    return True


def _midia_compativel(filtro: FiltroPreco, midia_row: str) -> bool:
    if not filtro.midia:
        return True
    m = _normalizar_midia(midia_row)
    if filtro.midia == m:
        return True
    if filtro.midia == "cartao":
        return m == "cartao"
    if filtro.midia == "token":
        return m == "token"
    if filtro.midia == "sem_midia":
        return m in ("sem_midia", "")
    if filtro.armazenamento == "A1" and filtro.midia == "arquivo":
        return m in ("arquivo", "")
    if filtro.midia == "nuvem":
        return m == "nuvem"
    return False


def parse_preferencias_form(form, *, tipo_arm: str = "A1") -> dict:
    """Lê preferências do formulário (cadastro ou jornada)."""
    emissao = (form.get("preferencia_emissao") or "videoconferencia").strip()
    if emissao not in EMISSOES_VALIDAS:
        emissao = "videoconferencia"

    try:
        validade = int(form.get("preferencia_validade_anos") or 1)
    except (TypeError, ValueError):
        validade = 1
    if validade not in OPCOES_VALIDADE:
        validade = 1

    midia = (form.get("preferencia_midia") or "").strip() or None
    opcoes = OPCOES_MIDIA_A3 if tipo_arm == "A3" else OPCOES_MIDIA_A1
    if midia not in {o[0] for o in opcoes}:
        midia = opcoes[0][0]

    return {
        "preferencia_emissao": emissao,
        "preferencia_validade_anos": validade,
        "preferencia_midia": midia,
    }


def consultar_catalogo(filtro: FiltroPreco) -> list[dict]:
    """Retorna preços do catálogo para os critérios do usuário."""
    rows = (
        _PrecoCatalogo.query.filter_by(
            produto_tipo=filtro.produto_tipo,
            categoria=filtro.categoria,
            armazenamento=filtro.armazenamento,
            validade_anos=filtro.validade_anos,
        )
        .order_by(_PrecoCatalogo.preco.asc())
        .all()
    )

    por_cert: dict = {}
    for row in rows:
        if not _emissao_compativel(filtro, row.emissao or ""):
            continue
        if not _midia_compativel(filtro, row.midia):
            continue
        atual = por_cert.get(row.certificadora)
        if not atual or row.preco < atual.preco:
            por_cert[row.certificadora] = row

    resultados: list[dict] = []
    for key, cert in certificadoras_ativas().items():
        row = por_cert.get(key)
        if row:
            resultados.append({
                "certificadora": key,
                "nome": cert["nome"],
                "produto_id": filtro.produto_id,
                "ok": True,
                "preco": row.preco,
                "preco_formatado": _formatar_preco(row.preco),
                "url": row.url or url_certificadora(key, filtro.armazenamento, filtro.categoria),
                "observacao": (
                    f"{row.observacao or ''} Catálogo atualizado em "
                    f"{row.atualizado_em.strftime('%d/%m/%Y %H:%M') if row.atualizado_em else '—'}."
                ).strip(),
                "instrucao": cert.get(f"instrucao_{filtro.armazenamento.lower()}", ""),
                "atualizado_em": row.atualizado_em.strftime("%d/%m/%Y %H:%M") if row.atualizado_em else "",
                "fonte": "catalogo",
            })
        else:
            resultados.append({
                "certificadora": key,
                "nome": cert["nome"],
                "produto_id": filtro.produto_id,
                "ok": False,
                "erro": "Preço não disponível no catálogo para esta combinação.",
                "url": url_certificadora(key, filtro.armazenamento, filtro.categoria),
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


def aplicar_precos_catalogo_vet(vet, db_session) -> list[dict]:
    """Consulta catálogo e grava em precos_json do usuário."""
    filtro = filtros_de_vet(vet)
    resultados = consultar_catalogo(filtro)
    import json

    vet.precos_json = json.dumps(resultados, ensure_ascii=False)
    melhor = next((r for r in resultados if r.get("melhor_preco")), None)
    if melhor:
        vet.certificadora_recomendada = melhor["certificadora"]
    db_session.commit()
    return resultados


SEED_PATH = os.path.join(os.path.dirname(__file__), "data", "catalogo_seed.json")


def exportar_catalogo_seed(caminho: str | None = None) -> int:
    """Exporta catálogo para JSON (deploy com preços prontos)."""
    import json

    path = caminho or SEED_PATH
    rows = _PrecoCatalogo.query.all()
    payload = {
        "exportado_em": datetime.utcnow().isoformat(),
        "itens": [
            {
                "chave": r.chave,
                "certificadora": r.certificadora,
                "produto_tipo": r.produto_tipo,
                "categoria": r.categoria,
                "armazenamento": r.armazenamento,
                "midia": r.midia,
                "emissao": r.emissao,
                "validade_anos": r.validade_anos,
                "preco": r.preco,
                "url": r.url,
                "observacao": r.observacao,
                "fonte": r.fonte,
            }
            for r in rows
        ],
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(payload["itens"])


def importar_catalogo_seed(caminho: str | None = None) -> int:
    """Carrega seed JSON se o catálogo estiver vazio."""
    import json

    path = caminho or SEED_PATH
    if not os.path.isfile(path):
        return 0
    if _PrecoCatalogo.query.count() > 0:
        return 0
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    n = 0
    for item in payload.get("itens", []):
        _upsert_preco(
            certificadora=item["certificadora"],
            produto_tipo=item["produto_tipo"],
            categoria=item["categoria"],
            armazenamento=item["armazenamento"],
            midia=item.get("midia") or "",
            emissao=item.get("emissao") or "videoconferencia",
            validade_anos=int(item.get("validade_anos") or 1),
            preco=float(item["preco"]),
            url=item.get("url") or "",
            observacao=item.get("observacao") or "",
            fonte=item.get("fonte") or "seed",
        )
        n += 1
    meta = _CatalogoMeta.query.first()
    if not meta:
        meta = _CatalogoMeta()
        _db.session.add(meta)
    meta.status = "ok"
    meta.concluido_em = datetime.utcnow()
    meta.itens_total = n
    meta.erro = None
    _db.session.commit()
    return n
