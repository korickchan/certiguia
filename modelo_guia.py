"""Gera guia de implementação personalizado (HTML para impressão/download)."""

from datetime import datetime

from guia_passos import guia_implementar_certificado, legislacao_por_profissao
from recomendacao import PROFISSOES, tipo_certificado_efetivo


def gerar_html_guia(vet, produto, cert_nome: str) -> str:
    profissao = getattr(vet, "profissao", None) or ("veterinario" if vet.eh_veterinario else "outro")
    prof = PROFISSOES.get(profissao, PROFISSOES["outro"])
    registro = vet.crmv if vet.crmv and vet.crmv != "—" else "____________"
    registro_uf = vet.crmv_uf if vet.crmv_uf and vet.crmv_uf != "NA" else "___"
    leg = legislacao_por_profissao(profissao)
    passos_impl = guia_implementar_certificado(
        profissao,
        tipo_certificado_efetivo(vet),
        getattr(vet, "sistema_receituario", None) or "",
    )
    produto_nome = produto["nome"] if produto else f"e-CPF {tipo_certificado_efetivo(vet)}"

    itens_leg = "".join(f"<li>{i}</li>" for i in leg["itens"])
    passos_html = "".join(f"<li>{p}</li>" for p in passos_impl)
    links_leg = "".join(f'<li><a href="{u}">{t}</a></li>' for t, u in leg.get("links", []))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Guia de implementação — {vet.protocolo}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 720px; margin: 2rem auto; padding: 0 1.5rem; color: #1e293b; line-height: 1.6; }}
h1 {{ font-size: 1.5rem; border-bottom: 2px solid #0d9488; padding-bottom: 0.5rem; }}
h2 {{ font-size: 1.15rem; margin-top: 1.75rem; color: #0f766e; }}
.meta {{ background: #f8fafc; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
.aviso {{ background: #fffbeb; border: 1px solid #fde68a; padding: 1rem; border-radius: 8px; font-size: 0.9rem; }}
@media print {{ body {{ margin: 1cm; }} }}
</style>
</head>
<body>
<h1>Guia de implementação — certificado digital</h1>
<p>Protocolo <strong>{vet.protocolo}</strong> · Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>

<div class="meta">
<p><strong>Profissional:</strong> {vet.nome_completo}<br>
<strong>CPF:</strong> {vet.cpf}<br>
<strong>{prof["registro"]}:</strong> {registro}-{registro_uf}<br>
<strong>E-mail:</strong> {vet.email}<br>
<strong>Certificado recomendado:</strong> {produto_nome}<br>
<strong>Certificadora escolhida:</strong> {cert_nome}</p>
</div>

<div class="aviso">
<strong>Atenção:</strong> Este documento é um guia orientativo, não substitui receituário oficial.
Modelos de receita controlada (azul, amarela, NRV etc.) devem seguir normas da Anvisa, MAPA, CFMV
e do seu conselho profissional. Consulte sempre a legislação vigente.
</div>

<h2>1. Legislação — {leg["titulo"]}</h2>
<ul>{itens_leg}</ul>
<ul>{links_leg}</ul>

<h2>2. Como implementar o certificado no seu receituário/sistema</h2>
<ol>{passos_html}</ol>

<h2>3. Validação no ITI (após assinar um documento)</h2>
<p>Depois de configurar o sistema e assinar um PDF de teste, valide no site oficial:</p>
<ol>
<li>Clique em «Escolher arquivo» e envie o <strong>PDF já assinado</strong> (arquivo completo).</li>
<li>Deixe «Assinatura destacada» desmarcada, salvo se seu software gera assinatura separada (.p7s).</li>
<li>Confirme que o resultado indica assinatura válida ICP-Brasil.</li>
</ol>
<p><a href="https://validar.iti.gov.br/" style="display:inline-block;background:#0d9488;color:#fff;padding:0.65rem 1rem;border-radius:8px;text-decoration:none;font-weight:700;">Abrir validar.iti.gov.br →</a></p>

<h2>4. Checklist final</h2>
<ul>
<li>Certificado instalado e senha testada</li>
<li>Documento teste assinado com selo ICP-Brasil</li>
<li>QR Code validado em validar.iti.gov.br</li>
<li>Sistema de receituário configurado</li>
<li>Numeração de controlados conforme norma da sua área (se aplicável)</li>
</ul>

<p style="margin-top:2rem;font-size:0.85rem;color:#64748b;">
CertiGuia — orientação gratuita para certificado digital.
</p>
</body>
</html>"""
