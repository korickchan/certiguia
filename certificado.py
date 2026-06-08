"""Certificadoras, tipos de certificado e orientações para veterinários."""

# ── Qual certificado o veterinário precisa? ───────────────────────────────────

TIPOS_CERTIFICADO = [
    {
        "id": "e-cpf-a1",
        "tipo_armazenamento": "A1",
        "nome": "e-CPF A1",
        "recomendado": True,
        "resumo": "Certificado da pessoa física (CPF), salvo no computador.",
        "validade": "1 ano",
        "indicado_para": "Consultório fixo — opção mais usada e mais barata.",
        "no_site": "Procure por «e-CPF A1» ou «A1 em arquivo».",
    },
    {
        "id": "e-cpf-a3",
        "tipo_armazenamento": "A3",
        "nome": "e-CPF A3",
        "recomendado": False,
        "resumo": "Certificado da pessoa física (CPF), em token USB ou cartão.",
        "validade": "1 a 3 anos",
        "indicado_para": "Quem usa o certificado em vários computadores.",
        "no_site": "Procure por «e-CPF A3» ou «A3 token/cartão».",
    },
]

TIPOS_NAO_USAR = [
    {
        "nome": "e-CNPJ A1 / A3",
        "motivo": "É certificado da clínica/empresa (CNPJ), não do veterinário como pessoa física. Não serve para assinar receita em nome próprio.",
    },
    {
        "nome": "e-PJ A1 / A3",
        "motivo": "Mesma lógica do e-CNPJ — pessoa jurídica. Para receituário veterinário com QR Code, o correto é e-CPF.",
    },
]

TIPO_PADRAO_VET = "A1"  # armazenamento A1 → produto e-CPF A1

# ── Verificação ICP-Brasil (ITI) ─────────────────────────────────────────────

ITI_REPOSITORIO = "https://www.gov.br/iti/pt-br/assuntos/repositorio"
ITI_LISTA_AC = "https://www.gov.br/iti/pt-br/assuntos/credenciamento/dpc-s-pc-s-hashes"
ITI_VALIDAR = "https://validar.iti.gov.br/"


def url_iti_certificadora(certificadora_key: str) -> str:
    """Link oficial para conferir a AC no cadastro do ITI."""
    cert = CERTIFICADORAS.get(certificadora_key, {})
    return cert.get("iti_url") or ITI_LISTA_AC


def ac_credenciada_iti(certificadora_key: str) -> bool:
    cert = CERTIFICADORAS.get(certificadora_key, {})
    return bool(cert.get("ativa", True) and cert.get("icp_brasil", False))


def aviso_icp_certificadora(certificadora_key: str) -> str | None:
    if ac_credenciada_iti(certificadora_key):
        return None
    cert = CERTIFICADORAS.get(certificadora_key, {})
    return (
        cert.get("aviso_icp")
        or cert.get("motivo_inativa")
        or "Não consta como AC ativa ICP-Brasil. Confira no ITI antes de comprar."
    )


def rotulo_icp_certificadora(certificadora_key: str) -> str:
    cert = CERTIFICADORAS.get(certificadora_key, {})
    return cert.get("nome_ac_iti") or cert.get("nome", "AC")


# ── Certificadoras (URLs corretas informadas pelo usuário) ────────────────────

CERTIFICADORAS = {
    "certisign": {
        "nome": "Certisign",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Certisign",
        "url_a1": "https://certisign.com.br/certificados/e-cpf/?codRev=96433&cod_rev=96433",
        "url_a3": "https://certisign.com.br/certificados/e-cpf/?codRev=96433&cod_rev=96433",
        "instrucao_a1": "Na página, selecione e-CPF → modelo A1 (arquivo no computador, 1 ano).",
        "instrucao_a3": "Na página, selecione e-CPF → modelo A3 (token ou cartão).",
        "preco_a1_label": "Ver preço no site (promoções variam)",
        "preco_a3_label": "Ver preço no site (promoções variam)",
    },
    "valid": {
        "nome": "Valid",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Valid",
        "url_a1": "https://validcertificadora.com.br/search?type=product%2Carticle%2Cpage&options%5Bprefix%5D=last&q=a1",
        "url_a3": "https://validcertificadora.com.br/search?type=product%2Carticle%2Cpage&options%5Bprefix%5D=last&q=a3",
        "instrucao_a1": "Na busca, escolha e-CPF A1 (certificado em arquivo, pessoa física).",
        "instrucao_a3": "Na busca, escolha e-CPF A3 (token/cartão, pessoa física).",
        "preco_a1_label": "Ver preço no site",
        "preco_a3_label": "Ver preço no site",
    },
    "safeweb": {
        "nome": "Safeweb",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Safeweb",
        "url_a1": "https://www.safeweb.com.br/produtos/checkout/ecpf",
        "url_a3": "https://www.safeweb.com.br/produtos/checkout/ecpf",
        "url_cnpj_a1": "https://www.safeweb.com.br/produtos/checkout/ecnpj",
        "url_cnpj_a3": "https://www.safeweb.com.br/produtos/checkout/ecnpj",
        "instrucao_a1": "No checkout, selecione e-CPF → emissão desejada → validade 1 ano → e-CPF A1 (arquivo).",
        "instrucao_a3": "No checkout, selecione e-CPF → Renovação ou Videoconferência → 1 ano → e-CPF A3 (sem mídia).",
        "preco_a1_label": "Checkout: e-CPF A1, 1 ano",
        "preco_a3_label": "Checkout: e-CPF A3 sem mídia, 1 ano",
    },
    "certclick": {
        "nome": "CertClick",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "CertClick (revenda ICP-Brasil)",
        "url_a1": "https://certclick.com.br/",
        "url_a3": "https://certclick.com.br/",
        "instrucao_a1": "Escolha «e-CPF A1» → Arquivo 1 ano → Compre agora.",
        "instrucao_a3": "Escolha «e-CPF A3» (requer token ou smart card).",
        "preco_a1_label": "Preço à vista no site",
        "preco_a3_label": "Preço à vista no site",
    },
    "serpro": {
        "nome": "Serpro",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Serpro",
        "url_a1": "https://servicos.serpro.gov.br/loja/certificacao-digital/",
        "url_a3": "https://servicos.serpro.gov.br/loja/certificacao-digital/",
        "instrucao_a1": "Loja Serpro → e-CPF A1 (arquivo, 1 ano). Compra e validação por videoconferência.",
        "instrucao_a3": "Loja Serpro → e-CPF A3 (token/cartão).",
        "preco_a1_label": "Tabela oficial Serpro",
        "preco_a3_label": "Tabela oficial Serpro",
    },
    "soluti": {
        "nome": "Soluti",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Soluti",
        "url_a1": "https://www.soluti.com.br/certificado-digital/e-cpf",
        "url_a3": "https://www.soluti.com.br/certificado-digital/e-cpf",
        "url_cnpj_a1": "https://www.soluti.com.br/certificado-digital/e-cnpj",
        "url_cnpj_a3": "https://www.soluti.com.br/certificado-digital/e-cnpj",
        "instrucao_a1": "Loja Soluti → «Certificado PF A1» (pessoa física, arquivo 1 ano).",
        "instrucao_a3": "Loja Soluti → «Certificado PF A3» (token/cartão).",
        "preco_a1_label": "Preço na loja oficial",
        "preco_a3_label": "Preço na loja oficial",
    },
    "digitalsign": {
        "nome": "DigitalSign",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Digitalsign",
        "url_a1": "https://digitalsigncertificadora.com.br/",
        "url_a3": "https://digitalsigncertificadora.com.br/",
        "instrucao_a1": "Card «e-CPF A1» → 1 ano em software → Comprar.",
        "instrucao_a3": "Card «e-CPF A3» conforme modalidade (nuvem, token ou cartão).",
        "preco_a1_label": "Preço à vista no site",
        "preco_a3_label": "Preço à vista no site",
    },
    "link": {
        "nome": "Link Certificação",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Link",
        "url_a1": "https://compras.linkcertificacao.com.br/aclink/cpf/",
        "url_a3": "https://compras.linkcertificacao.com.br/aclink/cpf/",
        "url_cnpj_a1": "https://compras.linkcertificacao.com.br/aclink/cnpj/",
        "url_cnpj_a3": "https://compras.linkcertificacao.com.br/aclink/cnpj/",
        "instrucao_a1": "Pessoa Física (e-CPF) → «Sem Mídia A1» (arquivo, 12 meses) → Comprar certificado.",
        "instrucao_a3": "Pessoa Física (e-CPF) → escolha A3 token ou cartão conforme sua mídia.",
        "preco_a1_label": "Preço na loja oficial Link",
        "preco_a3_label": "Preço na loja oficial Link",
    },
    "online": {
        "nome": "Online Certificadora",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Online Sul",
        "url_a1": "https://www.onlinesulcertificadora.com.br/PRODUTO/e-CPF",
        "url_a3": "https://www.onlinesulcertificadora.com.br/PRODUTO/e-CPF/E-CPF_A3_DE_1_ANO-21",
        "instrucao_a1": "Escolha «E-CPF A1» → Arquivo → 12 meses → aceite os termos e continue a compra.",
        "instrucao_a3": "Escolha «E-CPF A3» (requer token ou cartão ICP-Brasil compatível).",
        "preco_a1_label": "Preço à vista no site",
        "preco_a3_label": "Preço à vista no site",
    },
    "acdigital": {
        "nome": "AC Digital",
        "ativa": True,
        "icp_brasil": True,
        "nome_ac_iti": "AC Digital",
        "url_a1": "https://acdigital.com.br/certificado-digital/pessoa-fisica/e-pf-a1-teste.html",
        "url_a3": "https://acdigital.com.br/certificado-digital/pessoa-fisica/e-pf-a3-teste.html",
        "url_cnpj_a1": "https://acdigital.com.br/certificado-digital/pessoa-juridica/e-pj-a1-teste.html",
        "url_cnpj_a3": "https://acdigital.com.br/certificado-digital/pessoa-juridica/e-pj-a3-teste.html",
        "instrucao_a1": "Produto «e-PF A1» / e-CPF A1 → Comprar → conclua no checkout AC Digital.",
        "instrucao_a3": "Produto «e-PF A3» → Comprar (token/cartão conforme modalidade).",
        "preco_a1_label": "Checkout e-PF A1 (emissão presencial)",
        "preco_a3_label": "Checkout e-PF A3 (emissão presencial)",
    },
    "serasa": {
        "nome": "Serasa Experian",
        "ativa": False,
        "icp_brasil": False,
        "nome_ac_iti": "AC Serasa (inativa para novos certificados)",
        "aviso_icp": "A Serasa não comercializa novos certificados digitais. Não compre por este canal — escolha outra AC credenciada no ITI.",
        "motivo_inativa": "Não comercializa novos certificados digitais.",
        "url_a1": "",
        "url_a3": "",
        "instrucao_a1": "",
        "instrucao_a3": "",
        "preco_a1_label": "—",
        "preco_a3_label": "—",
    },
}

ETAPAS_CERTIFICADO = [
    ("cadastrado", "Cadastrado", "Dados registrados no sistema"),
    ("orientado", "Orientado", "Veterinário informado sobre e-CPF e certificadora"),
    ("pedido_certificadora", "Pedido feito", "Comprou e-CPF no site da certificadora"),
    ("validacao", "Validação", "Videoconferência ou presencial"),
    ("certificado_emitido", "Certificado emitido", "e-CPF emitido pela certificadora"),
    ("instalado", "Instalado", "Certificado instalado no PC ou token"),
    ("concluido", "Concluído", "Já consegue emitir receita com QR Code"),
]

ETAPAS_RECEITUARIO = [
    ("nao_solicitado", "Não aplicável", ""),
    ("pesquisando", "Pesquisando fornecedor", "Bloco físico é produto separado"),
    ("solicitado", "Solicitado", "Pedido feito a fornecedor"),
    ("entregue", "Entregue", "Recebido pelo veterinário"),
]


def certificadoras_ativas():
    return {k: v for k, v in CERTIFICADORAS.items() if v.get("ativa", True)}


def info_tipo(tipo_armazenamento):
    """Retorna dict do tipo e-CPF A1 ou A3."""
    for t in TIPOS_CERTIFICADO:
        if t["tipo_armazenamento"] == tipo_armazenamento:
            return t
    return TIPOS_CERTIFICADO[0]


def label_certificado(tipo_armazenamento):
    return info_tipo(tipo_armazenamento)["nome"]


def url_certificadora(certificadora_key, tipo, categoria="pf"):
    cert = CERTIFICADORAS.get(certificadora_key, CERTIFICADORAS["certisign"])
    if not cert.get("ativa", True):
        cert = CERTIFICADORAS["certisign"]
    if categoria == "pj":
        chave = "url_cnpj_a3" if tipo == "A3" else "url_cnpj_a1"
        if cert.get(chave):
            return cert[chave]
    return cert["url_a3"] if tipo == "A3" else cert["url_a1"]


def instrucao_compra(certificadora_key, tipo):
    cert = CERTIFICADORAS.get(certificadora_key, CERTIFICADORAS["certisign"])
    chave = "instrucao_a3" if tipo == "A3" else "instrucao_a1"
    return cert.get(chave, "")


def preco_label(certificadora_key, tipo):
    cert = CERTIFICADORAS.get(certificadora_key, CERTIFICADORAS["certisign"])
    chave = "preco_a3_label" if tipo == "A3" else "preco_a1_label"
    return cert.get(chave, "Ver preço no site")


def calcular_valores(tipo_certificado, certificadora_key=None, **_kwargs):
    cert = CERTIFICADORAS.get(certificadora_key or "certisign", CERTIFICADORAS["certisign"])
    if not cert.get("ativa", True):
        cert = CERTIFICADORAS["certisign"]
    tipo_info = info_tipo(tipo_certificado)
    return {
        "nome_produto": tipo_info["nome"],
        "preco_label": preco_label(certificadora_key or "certisign", tipo_certificado),
        "certificadora_nome": cert["nome"],
        "instrucao": instrucao_compra(certificadora_key or "certisign", tipo_certificado),
        "validade": tipo_info["validade"],
        "observacao": "Valor pago direto no site da certificadora. Confira o preço antes de comprar.",
    }


def dados_para_certificadora(vet):
    return {
        "nome_completo": vet.nome_completo,
        "cpf": vet.cpf,
        "rg": vet.rg or "",
        "data_nascimento": vet.data_nascimento.strftime("%d/%m/%Y") if vet.data_nascimento else "",
        "email": vet.email,
        "telefone": vet.telefone,
        "crmv": f"{vet.crmv}-{vet.crmv_uf}",
        "cep": vet.cep,
        "logradouro": vet.logradouro,
        "numero": vet.numero,
        "complemento": vet.complemento or "",
        "bairro": vet.bairro,
        "cidade": vet.cidade,
        "uf": vet.uf,
        "tipo_certificado": label_certificado(vet.tipo_certificado),
        "codigo_desconto": vet.codigo_desconto or "",
    }


def texto_pedido_certificadora(vet):
    dados = dados_para_certificadora(vet)
    cert_key = vet.certificadora or "certisign"
    linhas = [
        "=== COMPRA DE CERTIFICADO DIGITAL ===",
        "",
        "PRODUTO CORRETO: " + dados["tipo_certificado"],
        "(e-CPF = pessoa física / CPF — NÃO comprar e-CNPJ ou e-PJ)",
        "",
        instrucao_compra(cert_key, vet.tipo_certificado),
        "",
        f"Nome: {dados['nome_completo']}",
        f"CPF: {dados['cpf']}",
    ]
    if dados["rg"]:
        linhas.append(f"RG: {dados['rg']}")
    if dados["data_nascimento"]:
        linhas.append(f"Data nascimento: {dados['data_nascimento']}")
    linhas.extend([
        f"E-mail: {dados['email']}",
        f"Telefone: {dados['telefone']}",
        f"CRMV: {dados['crmv']}",
        "",
        f"Endereço: {dados['logradouro']}, {dados['numero']}",
    ])
    if dados["complemento"]:
        linhas.append(f"Complemento: {dados['complemento']}")
    linhas.extend([
        f"Bairro: {dados['bairro']}",
        f"Cidade/UF: {dados['cidade']}/{dados['uf']}",
        f"CEP: {dados['cep']}",
    ])
    if dados["codigo_desconto"]:
        linhas.append(f"\nCódigo de desconto (se houver): {dados['codigo_desconto']}")
    return "\n".join(linhas)


def texto_whatsapp_orientacao(vet):
    cert_key = vet.certificadora or "certisign"
    cert = CERTIFICADORAS.get(cert_key, CERTIFICADORAS["certisign"])
    tipo_info = info_tipo(vet.tipo_certificado)
    url = url_certificadora(cert_key, vet.tipo_certificado)
    primeiro_nome = vet.nome_completo.split()[0]

    return (
        f"Olá Dr(a). {primeiro_nome}!\n\n"
        f"Orientação para emitir receita com QR Code:\n\n"
        f"✅ COMPRE: *{tipo_info['nome']}*\n"
        f"   (certificado da *pessoa física* — seu CPF)\n\n"
        f"❌ NÃO COMPRE: e-CNPJ ou e-PJ\n"
        f"   (esses são da clínica/empresa, não servem para receita em seu nome)\n\n"
        f"📋 Modelo escolhido: *{tipo_info['nome']}*\n"
        f"   • {tipo_info['resumo']}\n"
        f"   • Validade: {tipo_info['validade']}\n\n"
        f"🛒 Onde comprar: *{cert['nome']}*\n"
        f"{url}\n\n"
        f"📝 No site: {instrucao_compra(cert_key, vet.tipo_certificado)}\n\n"
        f"📌 Seus dados:\n"
        f"   CPF: {vet.cpf}\n"
        f"   CRMV: {vet.crmv}-{vet.crmv_uf}\n\n"
        f"Depois da compra:\n"
        f"1. Agende videoconferência (validação de identidade)\n"
        f"2. Instale o certificado no computador\n"
        f"3. Pronto para emitir receita!\n\n"
        f"Dúvidas? Estou à disposição."
    )
