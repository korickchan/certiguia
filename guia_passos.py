"""Passo a passo por certificadora, instalação e receituário digital."""

ETAPAS_USUARIO = [
    ("recomendacao", "Recomendação"),
    ("precos", "Preços"),
    ("compra", "Compra"),
    ("software", "Software"),
    ("instalacao", "Instalação"),
    ("receituario", "Receituário"),
    ("validacao", "Validação ITI"),
    ("concluido", "Concluído"),
]

# ── Guias por certificadora ───────────────────────────────────────────────────

def _passos_compra(cert_nome, url, instrucao, tipo):
    return [
        {
            "titulo": f"Acessar {cert_nome}",
            "descricao": f"Abra o site oficial: {url}. Confirme que está no domínio correto antes de pagar.",
        },
        {
            "titulo": "Escolher o produto certo",
            "descricao": (
                instrucao
                + " No checkout, prefira Emissão: Videoconferência e Validade: 1 ano."
                + " Não confunda com SafeID Nuvem, e-CNPJ (se precisa e-CPF) ou outros produtos."
            ),
        },
        {
            "titulo": "Preencher dados pessoais",
            "descricao": "Informe CPF, nome completo (igual documento), e-mail, telefone e endereço. Revise tudo antes de pagar.",
        },
        {
            "titulo": "Pagamento",
            "descricao": "Pague com cartão, Pix ou boleto (conforme opções do site). Guarde comprovante e número do pedido.",
        },
        {
            "titulo": "Agendar validação",
            "descricao": f"Após pagamento, agende videoconferência ou atendimento presencial. Tenha RG ou CNH em mãos.",
        },
        {
            "titulo": f"Receber o {tipo}",
            "descricao": "A1: link por e-mail para baixar .pfx/.p12. A3: token/cartão enviado ou retirada conforme orientação da certificadora.",
        },
    ]


INSTALACAO_A1_GENERICO = [
    "Baixe o arquivo do certificado (.pfx ou .p12) do e-mail da certificadora.",
    "Clique duas vezes no arquivo ou use: certmgr.msc → Pessoal → Importar.",
    "Digite a senha que você definiu na certificadora.",
    "Faça backup do arquivo e da senha em local seguro.",
    "Reinicie o navegador ou o programa que usa o certificado.",
]

INSTALACAO_A3_GENERICO = [
    "Conecte o token USB ou insira o cartão na leitora.",
    "Instale o driver do token (link vem no e-mail da certificadora).",
    "Verifique em certmgr.msc se o certificado A3 aparece.",
    "Configure seu software para usar certificado A3 / token.",
    "Teste a assinatura antes de usar em receituário ou documentos oficiais.",
]

RECEITUARIO_A1_GENERICO = [
    "Configure o e-CPF A1 no seu software de assinatura ou receituário.",
    "Selecione o certificado instalado no Windows ou faça upload do arquivo .pfx.",
    "Valide em validar.iti.gov.br após a primeira emissão.",
]

RECEITUARIO_A3_GENERICO = [
    "Configure o e-CPF A3 (token ou cartão) no seu software de assinatura ou receituário.",
    "Conecte o token e informe a senha quando o sistema solicitar.",
    "Valide em validar.iti.gov.br após a primeira emissão.",
]


GUIAS_CERTIFICADORA = {
    "certisign": {
        "compra_a1": _passos_compra(
            "Certisign",
            "https://certisign.com.br/certificados/e-cpf/",
            "Selecione e-CPF → A1 (arquivo no computador, validade 1 ano).",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Certisign",
            "https://certisign.com.br/certificados/e-cpf/",
            "Selecione e-CPF → A3 (token USB ou cartão).",
            "e-CPF A3",
        ),
        "instalacao_a1": [
            "Baixe o arquivo .pfx do e-mail da Certisign.",
            "Instale o Certisign Agent se solicitado (link vem no e-mail).",
            "Clique duas vezes no .pfx ou use certmgr.msc → Pessoal → Importar.",
            "Digite a senha definida na compra. Marque exportação de chave privada para backup.",
            "Teste em validar.iti.gov.br com um PDF assinado.",
        ],
        "instalacao_a3": [
            "Instale o driver SafeNet ou indicado pela Certisign para seu token.",
            "Conecte o token USB e siga o assistente de instalação do certificado.",
            "Verifique em certmgr.msc se o certificado aparece.",
        ],
        "receituario_a1": [
            "No seu sistema de receituário, procure: Configurações → Certificado digital / Assinatura.",
            "Selecione certificado A1 instalado no Windows ou faça upload do arquivo .pfx.",
            "Informe a senha do certificado quando o sistema solicitar.",
            "Emita um documento teste e valide o QR Code em validar.iti.gov.br.",
        ],
    },
    "valid": {
        "compra_a1": _passos_compra(
            "Valid Certificadora",
            "https://validcertificadora.com.br/",
            "Na busca ou catálogo, escolha «e-CPF A1» (pessoa física, arquivo).",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Valid Certificadora",
            "https://validcertificadora.com.br/",
            "Escolha «e-CPF A3» (token ou cartão).",
            "e-CPF A3",
        ),
        "instalacao_a1": [
            "Baixe o .pfx do e-mail da Valid.",
            "Instale o Valid Driver (se indicado) a partir do site da certificadora.",
            "Importe via certmgr.msc ou assistente da Valid.",
            "Reinicie o navegador e o software que usará para assinar documentos.",
        ],
        "instalacao_a3": [
            "Instale driver do token conforme manual Valid.",
            "Importe certificado no token pelo software de gerenciamento.",
        ],
        "receituario_a1": [
            "Abra seu sistema de prescrição → área de certificado/assinatura.",
            "Vincule o e-CPF A1 (arquivo ou certificado do Windows).",
            "Faça emissão teste e confira selo ICP-Brasil + QR Code no PDF.",
        ],
    },
    "safeweb": {
        "compra_a1": _passos_compra(
            "Safeweb",
            "https://www.safeweb.com.br/produtos/checkout/ecpf",
            "Produto: e-CPF → Emissão: Videoconferência → Validade: 1 ano → Modelo A1 (mídia Arquivo).",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Safeweb",
            "https://www.safeweb.com.br/produtos/checkout/ecpf",
            "Produto: e-CPF → Emissão: Videoconferência → Validade: 1 ano → Modelo A3 (sem mídia ou cartão).",
            "e-CPF A3",
        ),
        "instalacao_a1": [
            "Baixe o certificado do e-mail Safeweb (.pfx).",
            "Instale middleware Safeweb se solicitado.",
            "Importe em certmgr.msc → Pessoal → Certificados.",
            "Guarde backup do .pfx e senha em local seguro.",
        ],
        "instalacao_a3": [
            "Instale driver do token Safeweb.",
            "Siga o manual de instalação do A3 enviado por e-mail.",
        ],
        "receituario_a1": [
            "Configure certificado A1 no software de receituário (upload .pfx ou seleção Windows).",
            "Para receitas controladas, confirme que o sistema exige assinatura qualificada ICP-Brasil.",
            "Valide documento gerado em validar.iti.gov.br antes de usar com pacientes.",
        ],
    },
    "certclick": {
        "compra_a1": _passos_compra(
            "CertClick",
            "https://certclick.com.br/",
            "Selecione «e-CPF A1» → Arquivo 1 ano → Compre agora.",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "CertClick",
            "https://certclick.com.br/",
            "Selecione «e-CPF A3» (requer token ou smart card).",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Configure o e-CPF A1 no seu software de assinatura ou receituário.",
            "Valide em validar.iti.gov.br após a primeira emissão.",
        ],
        "receituario_a3": [
            "No software, selecione certificado A3 (token ou cartão ICP-Brasil).",
            "Conecte o token e informe a senha quando solicitado.",
            "Valide em validar.iti.gov.br após a primeira emissão.",
        ],
    },
    "serpro": {
        "compra_a1": _passos_compra(
            "Serpro",
            "https://servicos.serpro.gov.br/loja/certificacao-digital/",
            "Na loja, marque os filtros: Pessoa Física (ou Jurídica) + Arquivo + 1 ano → card «e-CPF | A1 - 1 ano».",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Serpro",
            "https://servicos.serpro.gov.br/loja/certificacao-digital/",
            "Filtros: Pessoa Física + Somente o Certificado + 1 ano (se não aparecer, tente 2 anos — Serpro pode não listar A3 1 ano).",
            "e-CPF A3",
        ),
        "instalacao_a1": [
            "Baixe o .pfx pelo portal Serpro após validação cadastral.",
            "Importe via certmgr.msc ou assistente Serpro.",
            "Guarde backup do arquivo e senha.",
        ],
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Instale o certificado e configure no sistema que você usa.",
            "Serpro é Autoridade Certificadora oficial — válido em todo o Brasil.",
        ],
    },
    "soluti": {
        "compra_a1": _passos_compra(
            "Soluti",
            "https://www.soluti.com.br/loja",
            "Na loja, adicione «Certificado PF A1» ao carrinho (pessoa física, 1 ano).",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Soluti",
            "https://www.soluti.com.br/loja",
            "Escolha «Certificado PF A3» se precisar de token.",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Após emitir, configure o A1 no software que você utiliza.",
            "Soluti é uma das maiores ACs do país — certificado ICP-Brasil.",
        ],
    },
    "digitalsign": {
        "compra_a1": _passos_compra(
            "DigitalSign",
            "https://digitalsigncertificadora.com.br/",
            "Card «e-CPF A1» → 1 ano em software → Comprar.",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "DigitalSign",
            "https://digitalsigncertificadora.com.br/",
            "Escolha «e-CPF A3» (nuvem, token ou cartão).",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Instale o certificado e vincule ao seu sistema.",
            "DigitalSign é credenciada ICP-Brasil (RFB).",
        ],
    },
    "link": {
        "compra_a1": _passos_compra(
            "Link Certificação",
            "https://compras.linkcertificacao.com.br/aclink/cpf/",
            "Pessoa Física → «Sem Mídia A1» (arquivo, 12 meses). Validação online disponível se tiver CNH.",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Link Certificação",
            "https://compras.linkcertificacao.com.br/aclink/cpf/",
            "Escolha e-CPF A3 (token ou cartão). Verifique se já possui a mídia criptográfica.",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Configure o e-CPF A1 no software que você utiliza.",
            "Link é AC habilitada ICP-Brasil / RFB.",
        ],
    },
    "online": {
        "compra_a1": _passos_compra(
            "Online Certificadora",
            "https://www.onlinesulcertificadora.com.br/PRODUTO/e-CPF",
            "Selecione «E-CPF A1» → Arquivo → 12 meses → aceite os termos.",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "Online Certificadora",
            "https://www.onlinesulcertificadora.com.br/PRODUTO/e-CPF",
            "Selecione «E-CPF A3» (token/cartão ICP-Brasil compatível).",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Instale o certificado e configure no seu sistema.",
            "Online Certificadora é AC credenciada ICP-Brasil.",
        ],
    },
    "acdigital": {
        "compra_a1": _passos_compra(
            "AC Digital",
            "https://acdigital.com.br/certificado-digital/pessoa-fisica/e-pf-a1-teste.html",
            "Clique em «Comprar» no e-PF A1 e conclua o checkout (valor aparece na fatura).",
            "e-CPF A1",
        ),
        "compra_a3": _passos_compra(
            "AC Digital",
            "https://acdigital.com.br/certificado-digital/pessoa-fisica/e-pf-a3-teste.html",
            "Clique em «Comprar» no e-PF A3 e siga o checkout.",
            "e-CPF A3",
        ),
        "instalacao_a1": INSTALACAO_A1_GENERICO,
        "instalacao_a3": INSTALACAO_A3_GENERICO,
        "receituario_a1": [
            "Configure o certificado A1 no seu software.",
            "AC Digital é credenciada ICP-Brasil desde 2001.",
        ],
    },
}


DETALHES_COMPRA_CERTIFICADORA = {
    "safeweb": [
        "Produto: e-CPF (pessoa física) ou e-CNPJ (empresa) — ignore e-PF/e-PJ se aparecer.",
        "Emissão: Videoconferência (validação por vídeo, sem ir à loja).",
        "Validade: 1 ano.",
        "A1: mídia «Arquivo» (.pfx) · A3: «Sem mídia» ou cartão, conforme seu token.",
        "Não marque renovação se é a primeira emissão.",
    ],
    "certisign": [
        "Escolha e-CPF ou e-CNPJ conforme seu cadastro.",
        "Validade: 1 ano.",
        "Preferência: emissão por videoconferência quando disponível.",
        "A1: certificado em arquivo · A3: token USB/cartão.",
    ],
    "valid": [
        "Produto e-CPF/e-CNPJ A1 ou A3, validade 1 ano.",
        "Agende videoconferência após o pagamento.",
    ],
    "certclick": [
        "Selecione e-CPF A1 «Arquivo 1 ano» ou A3 conforme recomendação.",
        "Validação por videoconferência após pagamento.",
    ],
    "serpro": [
        "Na loja Serpro use os filtros à esquerda (não basta rolar a página).",
        "Tipo de cliente: Pessoa Física (e-CPF) ou Pessoa Jurídica (e-CNPJ).",
        "Tipo de certificado: Arquivo (A1) ou Somente o Certificado (A3).",
        "Tipo de produto: 1 ano (A3 pode aparecer só em 2 anos).",
        "Clique em «Iniciar» no card correto (ex.: e-CPF | A1 - 1 ano).",
        "Validação por videoconferência após contratação.",
    ],
    "soluti": [
        "Certificado PF (e-CPF), validade 1 ano, emissão por videoconferência.",
    ],
    "acdigital": [
        "Checkout eipar: e-PF/e-PJ, emissão presencial ou videoconferência — prefira videoconferência.",
        "Validade: 1 ano.",
    ],
    "digitalsign": [
        "e-CPF A1/A3, validade 1 ano, videoconferência após pagamento.",
    ],
    "link": [
        "Loja Link: e-CPF/e-CNPJ, validade 1 ano.",
        "Agende videoconferência quando disponível.",
    ],
    "online": [
        "Certificado ICP-Brasil, validade 1 ano, videoconferência.",
    ],
}


def detalhes_compra_certificadora(cert_key: str, tipo: str, categoria: str = "pf") -> dict:
    """Opções recomendadas no checkout após escolher a certificadora."""
    tipo = (tipo or "A1").upper()
    produto = "e-CNPJ" if categoria == "pj" else "e-CPF"
    midia = "Arquivo (.pfx no e-mail)" if tipo == "A1" else "Token USB ou cartão A3"
    itens = [
        f"Produto: {produto} {tipo}",
        f"Emissão: Videoconferência (preferencial)",
        f"Validade: 1 ano",
        f"Formato: {midia}",
    ]
    extras = DETALHES_COMPRA_CERTIFICADORA.get(cert_key, [])
    return {
        "titulo": "Opções no checkout — use exatamente isto",
        "itens": itens + list(extras),
    }


def guia_certificadora(cert_key: str, tipo: str, categoria: str = "pf") -> dict:
    """Retorna passos de compra, instalação e receituário para a certificadora."""
    cert = GUIAS_CERTIFICADORA.get(cert_key, GUIAS_CERTIFICADORA["certisign"])
    tipo = tipo.upper() if tipo else "A1"
    chave_tipo = "a1" if tipo == "A1" else "a3"
    receituario_padrao = RECEITUARIO_A1_GENERICO if tipo == "A1" else RECEITUARIO_A3_GENERICO
    return {
        "compra": cert.get(f"compra_{chave_tipo}", cert["compra_a1"]),
        "instalacao": cert.get(
            f"instalacao_{chave_tipo}",
            INSTALACAO_A1_GENERICO if tipo == "A1" else INSTALACAO_A3_GENERICO,
        ),
        "receituario": cert.get(f"receituario_{chave_tipo}", receituario_padrao),
        "detalhes_compra": detalhes_compra_certificadora(cert_key, tipo, categoria),
        "tipo": tipo,
    }


# ── Legislação receituário (referência) ───────────────────────────────────────

LEGISLACAO_RECEITUARIO = {
    "geral": {
        "titulo": "Receituário digital — visão geral",
        "itens": [
            "Documentos nato-digitais (gerados no sistema, não escaneados) têm validade quando assinados conforme a lei.",
            "Assinatura qualificada (ICP-Brasil, e-CPF/e-CNPJ) é exigida para documentos de controle especial.",
            "Assinatura avançada (ex.: gov.br) pode servir em casos específicos — confira a norma da sua área.",
        ],
        "links": [
            ("Anvisa — receitas eletrônicas", "https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr"),
        ],
    },
    "medico": {
        "titulo": "Medicina humana — receitas azuis/amarelas e SNCR",
        "itens": [
            "RDC Anvisa nº 1.000/2025 moderniza receituários de medicamentos controlados (Listas A, B, antimicrobianos etc.).",
            "Sistema Nacional de Controle de Receituários (SNCR): numeração e rastreabilidade centralizada pela Anvisa.",
            "Receitas de controle especial (ex.: notificações amarela/azul) exigem assinatura eletrônica qualificada (ICP-Brasil).",
            "Receituário eletrônico válido deve ser integrado ao SNCR — integração prevista a partir de jun/2026 (prazo até set/2026).",
            "Receita em papel continua existindo; o digital exige integração SNCR quando aplicável.",
            "Cadastre-se na Vigilância Sanitária local para obter numeração SNCR quando necessário.",
        ],
        "links": [
            ("SNCR — Anvisa", "https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr"),
            ("RDC 1.000/2025 — Perguntas e respostas", "https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/medicamentos/controlados/perguntas-e-respostas-rdc-1000-2025-1-ed.pdf"),
        ],
    },
    "veterinario": {
        "titulo": "Medicina veterinária — receitas controladas e QR Code",
        "itens": [
            "Resolução CFMV nº 1.465/2022: telemedicina e documentos digitais exigem assinatura eletrônica (qualificada para controlados).",
            "Portaria MAPA nº 837/2025: regime de controle especial veterinário; receitas digitais de controlados exigem certificado ICP-Brasil (e-CPF qualificado).",
            "Numeração sequencial de receitas controladas é responsabilidade do profissional — muitos sistemas automatizam (VetSoft, Prescreve, etc.).",
            "e-CPF A1 é o mais usado em softwares veterinários; assinatura gera PDF com selo ICP-Brasil e QR Code para validação.",
            "Assinatura avançada (gov.br) não substitui qualificada para receitas de controle especial veterinário.",
        ],
        "links": [
            ("CFMV", "https://www.cfmv.gov.br/"),
        ],
    },
    "outro": {
        "titulo": "Outras profissões",
        "itens": [
            "Contadores, advogados, engenheiros e demais profissões usam e-CPF ou e-CNPJ conforme emitem documentos (PF ou PJ).",
            "Para assinar contratos, procurações ou documentos fiscais, confira exigência do órgão receptor.",
            "e-CNPJ assina em nome da empresa; e-CPF assina como pessoa física profissional.",
        ],
        "links": [
        ],
    },
}


def legislacao_por_profissao(profissao: str) -> dict:
    if profissao == "veterinario":
        return LEGISLACAO_RECEITUARIO["veterinario"]
    if profissao == "medico":
        return LEGISLACAO_RECEITUARIO["medico"]
    if profissao in ("dentista", "farmaceutico", "enfermeiro"):
        return LEGISLACAO_RECEITUARIO["medico"]
    if profissao == "outro":
        return LEGISLACAO_RECEITUARIO["outro"]
    return LEGISLACAO_RECEITUARIO["geral"]


def guia_implementar_certificado(profissao: str, tipo: str, sistema: str = "") -> list[str]:
    """Passos genéricos para implementar certificado no receituário/sistema."""
    passos = [
        "Instale o certificado no Windows (A1) ou conecte o token (A3) conforme guia da certificadora.",
        "Abra o software ou plataforma onde você emite receitas/documentos.",
        "Localize: Configurações → Certificado digital, Assinatura ou Segurança.",
    ]
    if tipo == "A1":
        passos.append("Informe o arquivo .pfx ou selecione o certificado já instalado no Windows.")
    else:
        passos.append("Selecione certificado A3 / token e instale o driver se ainda não fez.")
    passos.extend([
        "Digite a senha do certificado quando solicitado (pode salvar no sistema se confiar no dispositivo).",
        "Emita um documento de teste (receita simples ou rascunho).",
        "Verifique se aparecem: selo ICP-Brasil, dados do signatário e QR Code (quando aplicável).",
        "Na seção «Validação no ITI» abaixo, envie esse PDF assinado ao validador oficial.",
    ])
    if profissao == "veterinario":
        passos.append("Para controlados: confirme numeração sequencial conforme Portaria MAPA 837/2025 no seu sistema.")
    if profissao == "medico":
        passos.append("Para controlados: verifique integração SNCR quando seu sistema/plataforma disponibilizar.")
    if sistema:
        passos.insert(3, f"No sistema «{sistema}», siga a documentação oficial de certificado digital.")
    return passos


# Compatibilidade com imports antigos
PASSOS_OBTENCAO = [
    {"num": i + 1, "titulo": p["titulo"], "descricao": p["descricao"]}
    for i, p in enumerate(_passos_compra("", "", "Confirme e-CPF ou e-CNPJ conforme recomendação.", "certificado"))
]
INSTALACAO_A1 = INSTALACAO_A1_GENERICO
INSTALACAO_A3 = INSTALACAO_A3_GENERICO
