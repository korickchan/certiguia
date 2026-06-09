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
    ("mobileid", "MobileID (app no celular)"),
]
OPCOES_MIDIA_A3 = [
    ("nuvem", "Nuvem (HSM) — celular/tablet"),
    ("token", "Token USB / pendrive"),
    ("cartao", "Cartão inteligente"),
    ("sem_midia", "Sem mídia física"),
]
OPCOES_MIDIA_CELULAR = [
    ("nuvem", "A3 em nuvem (HSM) — PC e celular"),
    ("mobileid", "A1 MobileID — app no celular"),
]

AJUDA_MIDIA_CELULAR = {
    "nuvem": (
        "Certificado A3 guardado na nuvem (HSM) da certificadora. "
        "Funciona no computador e no celular/tablet, pelo app de receituário. "
        "É o A3 indicado quando você precisa dos dois — não confunda com A3 token USB, "
        "que só serve em computadores com porta USB."
    ),
    "mobileid": (
        "Certificado A1 no app da certificadora no celular (MobileID). "
        "Não é A3 — é outra modalidade, em geral só no smartphone. "
        "Confira se o seu app de receituário aceita MobileID."
    ),
}
OPCOES_VALIDADE = [1, 2, 3]

MIDIAS_VALIDAS = {m[0] for m in OPCOES_MIDIA_A1} | {m[0] for m in OPCOES_MIDIA_A3}
EMISSOES_VALIDAS = {e[0] for e in OPCOES_EMISSAO}

MIDIAS_MOVEIS = frozenset({"nuvem", "mobileid"})

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
        "Ideal se você usa sempre o mesmo PC ou notebook. "
        "Tecnicamente dá para importar o .pfx no iPhone ou Android (Gov.br, e-mail etc.), "
        "mas a maioria dos apps de receituário não usa esse formato — prefira nuvem ou MobileID."
    ),
    "nuvem": (
        "O certificado fica em servidores seguros da certificadora (HSM/nuvem), "
        "não no seu aparelho. Você acessa pela internet, de qualquer lugar — "
        "incluindo celular e tablet, via app de receituário ou navegador. "
        "É a opção mais prática para prescrição móvel e para quem não quer depender de um PC."
    ),
    "mobileid": (
        "Certificado A1 pensado para celular/tablet, gerenciado pelo app da certificadora "
        "(ex.: Certisign mobileID, Valid Credentials). O certificado fica no aparelho móvel. "
        "Confira se o seu app de receituário aceita MobileID — nem todos integram. "
        "Diferente da nuvem (HSM): aqui o certificado está no smartphone, não nos servidores da AC."
    ),
}

AJUDA_MIDIA_A3 = {
    "nuvem": (
        "Certificado A3 em nuvem (HSM): fica nos servidores da certificadora e você acessa "
        "pelo app de receituário no celular, tablet ou PC. "
        "É o formato que a maioria das ACs vende para uso móvel — não confunda com token USB."
    ),
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
    "Certificado A1 — arquivo no PC, nuvem (HSM) ou MobileID (app no celular). "
    "Para receituário móvel, prefira nuvem ou MobileID."
)

AJUDA_SECAO_A3 = (
    "Certificado A3 — nuvem (HSM) para celular, ou token/cartão para vários PCs. "
    "Para receituário no smartphone, escolha nuvem — token USB não funciona no celular."
)

AJUDA_ONDE_USAR_INTRO = (
    "Escolha onde você vai assinar receitas e documentos. "
    "Isso define o tipo de certificado — errar aqui leva a comprar o produto errado."
)

AJUDA_WIZARD_INTRO = (
    "Uma pergunta por vez, sem jargão. Com base nas suas respostas, "
    "no final indicamos o certificado adequado e comparamos preços entre certificadoras."
)

AJUDA_PROFISSAO = {
    "veterinario": (
        "Receituário animal, laudos e documentos profissionais em seu nome "
        "usam certificado e-CPF (CPF), credenciado ICP-Brasil."
    ),
    "medico": (
        "Receitas, prontuário e documentos clínicos em seu nome exigem e-CPF (CPF) "
        "com validade jurídica ICP-Brasil."
    ),
    "dentista": (
        "Documentos odontológicos, receitas e laudos em seu nome profissional "
        "usam e-CPF (CPF)."
    ),
    "farmaceutico": (
        "Dispensação, documentos farmacêuticos e assinaturas profissionais "
        "em geral usam e-CPF (CPF)."
    ),
    "contador": (
        "Obrigações fiscais da empresa costumam exigir e-CNPJ; "
        "documentos pessoais do contador usam e-CPF."
    ),
    "advogado": (
        "Petições, contratos e documentos em seu nome usam e-CPF (CPF); "
        "documentos do escritório podem exigir e-CNPJ."
    ),
    "outro": (
        "A profissão ajuda a orientar receituário, fiscal ou uso geral — "
        "ajustamos a recomendação conforme sua resposta."
    ),
}

AJUDA_FINALIDADE = {
    "receituario": (
        "Emitir receitas digitais, prescrições ou receituário de controle especial. "
        "Quase sempre exige e-CPF; no celular, prefira nuvem ou MobileID."
    ),
    "documentos": (
        "Assinar contratos, laudos, termos e documentos profissionais "
        "com validade jurídica."
    ),
    "fiscal": (
        "Nota fiscal eletrônica, SPED, e-CAC e demais obrigações da empresa — "
        "em geral e-CNPJ (CNPJ da clínica ou empresa)."
    ),
    "geral": (
        "Vários usos (Gov.br, e-mail, sistemas diversos). "
        "Indicamos o tipo mais versátil conforme onde você for usar."
    ),
}

AJUDA_EMITE_COMO = {
    "pf": (
        "Receituário, laudos e documentos em seu nome profissional usam e-CPF (CPF). "
        "Indicado se você não emite pela clínica/empresa."
    ),
    "pj": (
        "Documentos em nome da clínica ou empresa (NF-e, contratos da PJ etc.) "
        "usam e-CNPJ (CNPJ). Receitas em seu nome ainda precisam de e-CPF."
    ),
    "ambos": (
        "Você emite tanto em seu CPF quanto pelo CNPJ da clínica/empresa — "
        "pode precisar dos dois certificados."
    ),
}

PERGUNTA_WIZARD = {
    "profissao": "Qual é sua área de atuação?",
    "finalidade": "Para que você precisa do certificado digital?",
    "onde": "Onde você vai usar para assinar documentos?",
    "titular": "Em nome de quem você emite documentos?",
    "formato": "PC e celular — qual formato?",
    "emissao": "Como prefere validar sua identidade na certificadora?",
    "dados": "Seus dados para gerar o guia personalizado",
}

CONTEXTO_WIZARD = {
    "profissao": "Sua profissão define se o foco é receituário, fiscal ou documentos em geral.",
    "finalidade": "O uso principal evita comprar e-CPF quando precisa de e-CNPJ, ou vice-versa.",
    "onde": "Onde você vai assinar define o tipo certo — A3 token e A3 nuvem não são a mesma coisa.",
    "titular": "CPF é seu nome profissional; CNPJ é a clínica ou empresa.",
    "formato": "Para PC e celular existem dois caminhos: A3 nuvem (HSM) ou A1 MobileID.",
    "emissao": "Afeta preço e praticidade — videoconferência costuma ser mais rápida.",
    "dados": "Usamos só para montar seu guia e salvar suas preferências. Não vendemos certificado.",
}

OPCOES_ONDE_USAR = [
    ("pc_unico", "Só em um computador (A1 em arquivo)"),
    ("varios_pc", "Vários computadores — sem celular (A3 token/cartão)"),
    ("pc_e_celular", "Computador e celular/tablet (A3 nuvem ou A1 MobileID)"),
]

AJUDA_ONDE_A3_AVISO = (
    "Atenção: nem todo A3 serve para celular. "
    "A3 com token USB funciona só em computadores. "
    "Para assinar no smartphone, o caminho é A3 em nuvem (HSM) ou A1 MobileID — opções diferentes."
)

AJUDA_ONDE_USAR = {
    "pc_unico": (
        "Indicamos e-CPF/e-CNPJ A1 em arquivo — costuma ser o mais barato. "
        "O certificado fica instalado naquele computador. "
        "Não é a melhor escolha se você precisa assinar no celular."
    ),
    "varios_pc": (
        "Indicamos e-CPF/e-CNPJ A3 com token USB ou cartão inteligente. "
        "Você conecta o dispositivo em cada computador da clínica ou escritório. "
        "Este A3 não funciona no celular — não há como plugar o token no smartphone. "
        "Se você também precisa do celular, volte e escolha «Computador e celular»."
    ),
    "pc_e_celular": (
        "Indicamos certificado que funciona no PC e no celular/tablet. "
        "Na prática são duas opções: A3 em nuvem (HSM), vendido pelas certificadoras como A3 nuvem, "
        "ou A1 MobileID (app no celular). "
        "Não compre A3 token pensando que vai funcionar no celular — só A3 nuvem ou MobileID servem."
    ),
}

AJUDA_VARIOS_COMPUTADORES = (
    "Vários computadores (sem celular) → A3 com token ou cartão: conecta o dispositivo "
    "em cada PC. Não funciona no smartphone. "
    "Computador e celular → A3 em nuvem (HSM) ou A1 MobileID — são outros produtos."
)

AJUDA_USO_CELULAR = (
    "Para assinar no PC e no celular, escolha A3 em nuvem (HSM) — é o A3 que as certificadoras "
    "vendem para uso móvel. A3 token USB não serve no celular. "
    "Alternativa: A1 MobileID (app da certificadora), em geral focado no smartphone."
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
    v = valor.lower().strip().replace("_", "-")
    compact = v.replace("-", "").replace(" ", "")
    if "mobileid" in compact or "mobileid" in v:
        return "mobileid"
    if "mobile" in v and "id" in compact:
        return "mobileid"
    if "nuvem" in v or v == "cloud" or "hsm" in v:
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


def _rotulo_formato(armazenamento: str, midia: str) -> str:
    midia_map = dict(OPCOES_MIDIA_A1 + OPCOES_MIDIA_A3)
    rotulo_midia = midia_map.get(midia, midia or "—")
    return f"{armazenamento} · {rotulo_midia}"


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


def _perfil_formato_celular(midia: str) -> tuple[str, str]:
    """MobileID → A1; nuvem (HSM) no celular → A3."""
    m = _normalizar_midia(midia)
    if m == "mobileid":
        return "A1", "mobileid"
    if m == "nuvem":
        return "A3", "nuvem"
    raise ValueError(f"Mídia não é formato celular: {midia}")


def uso_formato_celular(vet) -> bool:
    """Usuário escolheu uso no celular (nuvem ou MobileID), sem token em vários PCs."""
    if getattr(vet, "varios_computadores", False):
        return False
    m = _normalizar_midia(getattr(vet, "preferencia_midia", None))
    return m in MIDIAS_MOVEIS


def _sincronizar_vet_formato_celular(vet) -> None:
    """Alinha produto A1/A3 e mídia quando o perfil é celular/tablet."""
    from recomendacao import produto_id_efetivo

    if not uso_formato_celular(vet):
        return
    arm, midia = _perfil_formato_celular(vet.preferencia_midia)
    vet.preferencia_midia = midia
    pid = produto_id_efetivo(vet)
    categoria = PRODUTOS[pid]["categoria"] if pid in PRODUTOS else "pf"
    if getattr(vet, "emite_como", None) == "pj" and _cnpj_informado_vet(vet):
        categoria = "pj"
    elif getattr(vet, "emite_como", None) in ("pf", "ambos", None):
        categoria = "pf"
    familia = "cpf" if categoria == "pf" else "cnpj"
    vet.produto_recomendado = f"e-{familia}-{arm.lower()}"
    vet.tipo_certificado = arm


def _cnpj_informado_vet(vet) -> bool:
    if not getattr(vet, "cnpj", None):
        return False
    digitos = "".join(c for c in str(vet.cnpj) if c.isdigit())
    return len(digitos) == 14


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

    midia_atual = _normalizar_midia(getattr(vet, "preferencia_midia", None))
    if midia_atual in MIDIAS_MOVEIS and not getattr(vet, "varios_computadores", False):
        _sincronizar_vet_formato_celular(vet)
    else:
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

    if uso_formato_celular(vet):
        arm, midia = _perfil_formato_celular(midia or vet.preferencia_midia)
        return FiltroPreco(
            produto_id=pid,
            categoria=PRODUTOS[pid]["categoria"],
            armazenamento=arm,
            emissao=emissao,
            validade_anos=int(validade or 1),
            midia=midia,
        )

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
    from varredura_playwright import coletar_catalogo_completo

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
        linhas = coletar_catalogo_completo()
        for item in linhas:
            fonte = item.pop("fonte", "playwright")
            _upsert_preco(fonte=fonte, **item)
            total += 1
            if total % 40 == 0:
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
    if filtro.midia == "mobileid":
        return m == "mobileid"
    return False


def _entry_sem_preco(cert_key: str, cert: dict, filtro: FiltroPreco, *, formato: str = "") -> dict:
    arm = filtro.armazenamento or "A1"
    if not formato and filtro.midia in MIDIAS_MOVEIS:
        formato = _rotulo_formato(arm, filtro.midia)
    return {
        "certificadora": cert_key,
        "nome": cert.get("nome", cert_key),
        "formato": formato,
        "produto_id": filtro.produto_id,
        "ok": False,
        "erro": "Valor não encontrado para opção recomendada",
        "url": url_certificadora(cert_key, arm, filtro.categoria),
        "instrucao": cert.get(f"instrucao_{arm.lower()}", ""),
        "fonte": "catalogo",
    }


def _completar_certificadoras_sem_preco(resultados: list[dict], filtro: FiltroPreco) -> list[dict]:
    """Garante uma linha por AC — com preço ou link quando não houver no catálogo."""
    presentes = {r["certificadora"] for r in resultados}
    for key, cert in certificadoras_ativas().items():
        if key not in presentes:
            resultados.append(_entry_sem_preco(key, cert, filtro))
    com_preco = [r for r in resultados if r.get("ok")]
    if com_preco:
        menor = min(r["preco"] for r in com_preco)
        for r in resultados:
            r["melhor_preco"] = r.get("ok") and r["preco"] == menor
    else:
        for r in resultados:
            r["melhor_preco"] = False
    resultados.sort(key=lambda x: (not x.get("ok"), x.get("preco", 9999), x.get("nome", "")))
    return resultados


def _consultar_catalogo_midias_moveis(filtro: FiltroPreco) -> list[dict]:
    """Nuvem (A3) ou MobileID (A1) — só preços com mídia móvel explícita no catálogo."""
    arm_obrigatorio, midia_obrigatoria = _perfil_formato_celular(filtro.midia or "")
    rows = (
        _PrecoCatalogo.query.filter_by(
            produto_tipo=filtro.produto_tipo,
            categoria=filtro.categoria,
            validade_anos=filtro.validade_anos,
        )
        .order_by(_PrecoCatalogo.preco.asc())
        .all()
    )

    por_chave: dict[str, object] = {}
    for row in rows:
        m = _normalizar_midia(row.midia)
        if m not in MIDIAS_MOVEIS:
            continue
        if m != midia_obrigatoria:
            continue
        if row.armazenamento != arm_obrigatorio:
            continue
        if not _emissao_compativel(filtro, row.emissao or ""):
            continue
        chave = row.certificadora
        atual = por_chave.get(chave)
        if not atual or row.preco < atual.preco:
            por_chave[chave] = row

    resultados: list[dict] = []
    for row in sorted(por_chave.values(), key=lambda r: r.preco):
        cert = certificadoras_ativas().get(row.certificadora, {})
        formato = _rotulo_formato(row.armazenamento, _normalizar_midia(row.midia))
        resultados.append({
            "certificadora": row.certificadora,
            "nome": cert.get("nome", row.certificadora),
            "formato": formato,
            "produto_id": filtro.produto_id,
            "ok": True,
            "preco": row.preco,
            "preco_formatado": _formatar_preco(row.preco),
            "url": row.url or url_certificadora(
                row.certificadora, row.armazenamento, filtro.categoria
            ),
            "observacao": (
                f"{formato}. {row.observacao or ''} Catálogo atualizado em "
                f"{row.atualizado_em.strftime('%d/%m/%Y %H:%M') if row.atualizado_em else '—'}."
            ).strip(),
            "instrucao": cert.get(f"instrucao_{row.armazenamento.lower()}", ""),
            "atualizado_em": row.atualizado_em.strftime("%d/%m/%Y %H:%M") if row.atualizado_em else "",
            "fonte": "catalogo",
        })

    return _completar_certificadoras_sem_preco(resultados, filtro)


def parse_onde_usar_form(form) -> dict:
    """Mapeia escolha «onde usar» para varios_pc + preferencia_midia."""
    onde = (form.get("onde_usar") or "pc_unico").strip()
    if onde in ("celular", "pc_e_celular"):
        return {
            "varios_computadores": False,
            "usa_celular": True,
        }
    if onde == "varios_pc":
        return {
            "varios_computadores": True,
            "preferencia_midia": "token",
            "usa_celular": False,
        }
    return {
        "varios_computadores": False,
        "preferencia_midia": "arquivo",
        "usa_celular": False,
    }


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
    if filtro.midia in MIDIAS_MOVEIS:
        return _consultar_catalogo_midias_moveis(filtro)

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
            resultados.append(_entry_sem_preco(key, cert, filtro))

    return _completar_certificadoras_sem_preco(resultados, filtro)


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

# Preços MobileID — upsert na subida (varredura automática não captura bem)
ITENS_FIXOS_CATALOGO = [
    {
        "certificadora": "certisign",
        "produto_tipo": "e-CPF",
        "categoria": "pf",
        "armazenamento": "A1",
        "midia": "mobileid",
        "emissao": "videoconferencia",
        "validade_anos": 1,
        "preco": 186.90,
        "url": "https://certisign.com.br/monte-seu-certificado-digital",
        "observacao": "Certisign — e-CPF A1 MobileID (celular/tablet), 12 meses.",
        "fonte": "fixo_mobileid",
    },
    {
        "certificadora": "soluti",
        "produto_tipo": "e-CPF",
        "categoria": "pf",
        "armazenamento": "A1",
        "midia": "mobileid",
        "emissao": "videoconferencia",
        "validade_anos": 1,
        "preco": 162.00,
        "url": "https://www.soluti.com.br/certificado-digital/a1/",
        "observacao": "Soluti — e-CPF A1 MobileID (app no celular), referência de mercado.",
        "fonte": "fixo_mobileid",
    },
    {
        "certificadora": "valid",
        "produto_tipo": "e-CPF",
        "categoria": "pf",
        "armazenamento": "A1",
        "midia": "mobileid",
        "emissao": "videoconferencia",
        "validade_anos": 1,
        "preco": 155.00,
        "url": "https://validcertificadora.com.br/",
        "observacao": "Valid — e-CPF A1 via app Valid Credentials (MobileID). Confira no site.",
        "fonte": "fixo_mobileid",
    },
]


def complementar_catalogo_fixos() -> int:
    """Garante itens fixos (ex.: MobileID) mesmo com catálogo já populado."""
    n = 0
    for item in ITENS_FIXOS_CATALOGO:
        _upsert_preco(
            certificadora=item["certificadora"],
            produto_tipo=item["produto_tipo"],
            categoria=item["categoria"],
            armazenamento=item["armazenamento"],
            midia=item["midia"],
            emissao=item["emissao"],
            validade_anos=item["validade_anos"],
            preco=item["preco"],
            url=item["url"],
            observacao=item["observacao"],
            fonte=item["fonte"],
        )
        n += 1
    if n:
        _db.session.commit()
    return n


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
