"""Motor de recomendação de certificado digital."""

PRODUTOS = {
    "e-cpf-a1": {
        "id": "e-cpf-a1",
        "nome": "e-CPF A1",
        "categoria": "pf",
        "tipo_armazenamento": "A1",
        "chave_preco": "e-cpf a1",
        "resumo": "Certificado da pessoa física (CPF), arquivo no computador.",
        "validade": "1 ano",
    },
    "e-cpf-a3": {
        "id": "e-cpf-a3",
        "nome": "e-CPF A3",
        "categoria": "pf",
        "tipo_armazenamento": "A3",
        "chave_preco": "e-cpf a3",
        "resumo": "Certificado da pessoa física (CPF), token USB ou cartão.",
        "validade": "1 a 3 anos",
    },
    "e-cnpj-a1": {
        "id": "e-cnpj-a1",
        "nome": "e-CNPJ A1",
        "categoria": "pj",
        "tipo_armazenamento": "A1",
        "chave_preco": "e-cnpj a1",
        "resumo": "Certificado da empresa/clínica (CNPJ), arquivo no computador.",
        "validade": "1 ano",
    },
    "e-cnpj-a3": {
        "id": "e-cnpj-a3",
        "nome": "e-CNPJ A3",
        "categoria": "pj",
        "tipo_armazenamento": "A3",
        "chave_preco": "e-cnpj a3",
        "resumo": "Certificado da empresa (CNPJ), token ou cartão.",
        "validade": "1 a 3 anos",
    },
}

PROFISSOES = {
    "veterinario": {"nome": "Médico(a) veterinário(a)", "registro": "CRMV"},
    "medico": {"nome": "Médico(a)", "registro": "CRM"},
    "dentista": {"nome": "Cirurgião(ã) dentista", "registro": "CRO"},
    "farmaceutico": {"nome": "Farmacêutico(a)", "registro": "CRF"},
    "contador": {"nome": "Contador(a)", "registro": "CRC"},
    "advogado": {"nome": "Advogado(a)", "registro": "OAB"},
    "outro": {"nome": "Outra profissão", "registro": "Registro profissional"},
}

FINALIDADES = {
    "receituario": "Receituário / prescrições digitais",
    "documentos": "Assinar documentos e contratos",
    "fiscal": "Nota fiscal / obrigações fiscais",
    "geral": "Uso geral (vários tipos)",
}


def _cnpj_informado(cnpj) -> bool:
    if not cnpj:
        return False
    digitos = "".join(c for c in str(cnpj) if c.isdigit())
    return len(digitos) == 14


def recomendar(
    *,
    profissao="outro",
    emite_como="pf",
    varios_computadores=False,
    finalidade="documentos",
    cnpj=None,
    eh_veterinario=None,
):
    """
    emite_como: 'pf' | 'pj' | 'ambos'
    finalidade: receituario | documentos | fiscal | geral
    eh_veterinario: legado — se True, trata como profissao veterinario
    """
    if eh_veterinario is True:
        profissao = "veterinario"
    elif eh_veterinario is False and profissao == "veterinario":
        profissao = "outro"

    armazenamento = "A3" if varios_computadores else "A1"
    observacoes = []
    tem_cnpj = _cnpj_informado(cnpj)
    precisa_pf_assinatura = finalidade in ("receituario", "documentos", "geral") or profissao in (
        "veterinario", "medico", "dentista", "farmaceutico", "advogado"
    )

    if emite_como in ("pj", "ambos") and not tem_cnpj:
        observacoes.append(
            "Para emitir pela clínica ou empresa, informe o CNPJ no cadastro. "
            "Se você trabalha só como pessoa física (sem CNPJ), marque «Como pessoa física (CPF)»."
        )

    if emite_como == "pf" or (emite_como in ("pj", "ambos") and not tem_cnpj and precisa_pf_assinatura):
        produto_id = f"e-cpf-{armazenamento.lower()}"
        secundario = f"e-cnpj-{armazenamento.lower()}" if emite_como == "ambos" and tem_cnpj else None
        if emite_como in ("pj", "ambos") and precisa_pf_assinatura:
            observacoes.append(
                "Receitas e documentos em seu nome profissional exigem e-CPF (CPF). "
                "O e-CNPJ serve para documentos em nome da empresa."
            )
    elif emite_como == "ambos" and tem_cnpj:
        produto_id = f"e-cpf-{armazenamento.lower()}"
        secundario = f"e-cnpj-{armazenamento.lower()}"
        observacoes.append(
            "Comece pelo e-CPF para documentos profissionais; e-CNPJ complementa documentos da empresa."
        )
    elif emite_como == "pj" and tem_cnpj:
        produto_id = f"e-cnpj-{armazenamento.lower()}"
        secundario = None
        if precisa_pf_assinatura:
            observacoes.append(
                "Para receituário ou assinatura em seu nome, você também precisará de e-CPF — "
                "considere marcar «Os dois (CPF e CNPJ)»."
            )
    else:
        produto_id = f"e-cpf-{armazenamento.lower()}"
        secundario = None

    if finalidade == "receituario" and profissao in ("veterinario", "medico", "dentista"):
        observacoes.append(
            "Receitas de controle especial exigem assinatura qualificada ICP-Brasil no CPF do profissional (e-CPF)."
        )
        observacoes.append(
            "Para assinar receituário no celular, prefira certificado na nuvem — "
            "não use token USB (A3 físico). Na comparação de preços, filtre «Nuvem (HSM)»."
        )

    produto = PRODUTOS[produto_id]
    motivo = _texto_motivo(
        produto, armazenamento, profissao, emite_como, varios_computadores, finalidade, tem_cnpj
    )

    return {
        "produto_id": produto_id,
        "produto": produto,
        "tipo_armazenamento": armazenamento,
        "motivo": motivo,
        "observacoes": observacoes,
        "secundario": PRODUTOS.get(secundario) if secundario else None,
    }


def produto_id_efetivo(vet) -> str:
    """ID do produto (e-cpf-a1, e-cnpj-a3, etc.) usado na busca de preços."""
    pid = getattr(vet, "produto_recomendado", None)
    if pid and pid in PRODUTOS:
        return pid
    tipo = (getattr(vet, "tipo_certificado", None) or "A1").lower()
    return f"e-cpf-{tipo}"


def tipo_certificado_efetivo(vet) -> str:
    """A1 ou A3 conforme o produto recomendado (fonte principal)."""
    pid = getattr(vet, "produto_recomendado", None)
    if pid and pid in PRODUTOS:
        return PRODUTOS[pid]["tipo_armazenamento"]
    return (getattr(vet, "tipo_certificado", None) or "A1").upper()


def produtos_comparacao(
    produto_id: str,
    *,
    emite_como: str = "pf",
    secundario_id: str | None = None,
    tem_cnpj: bool = False,
) -> dict:
    """Lista de produtos relevantes para comparar preços conforme o perfil."""
    if secundario_id:
        ids = [produto_id, secundario_id]
    elif emite_como == "pj" and tem_cnpj:
        ids = ["e-cnpj-a1", "e-cnpj-a3"]
    elif emite_como == "ambos" and tem_cnpj:
        ids = list(PRODUTOS.keys())
    else:
        ids = ["e-cpf-a1", "e-cpf-a3"]
    if produto_id not in ids:
        ids.insert(0, produto_id)
    vistos: list[str] = []
    for pid in ids:
        if pid in PRODUTOS and pid not in vistos:
            vistos.append(pid)
    return {pid: PRODUTOS[pid] for pid in vistos}


def _texto_motivo(
    produto,
    armazenamento,
    profissao,
    emite_como,
    varios_computadores,
    finalidade,
    tem_cnpj,
):
    prof = PROFISSOES.get(profissao, PROFISSOES["outro"])
    partes = [f"Indicamos {produto['nome']} porque você atua como {prof['nome'].lower()}."]
    if finalidade == "receituario":
        partes.append("Você precisa emitir receituário ou prescrições digitais.")
    elif finalidade == "fiscal":
        partes.append("Você precisa do certificado para obrigações fiscais ou NF-e.")
    if produto["categoria"] == "pf":
        partes.append("Você emite como pessoa física (CPF), sem certificado da clínica/empresa.")
    else:
        partes.append("Você emite pela empresa/clínica (CNPJ).")
    if emite_como in ("pj", "ambos") and produto["categoria"] == "pf" and tem_cnpj:
        partes.append(
            "Você indicou clínica/empresa, mas receitas e laudos em seu nome usam o e-CPF (CPF)."
        )
    if armazenamento == "A1":
        partes.append("Um computador principal — A1 costuma ser mais barato e prático.")
    else:
        partes.append("Vários computadores — A3 (token) facilita o uso em mais de um lugar.")
    return " ".join(partes)
