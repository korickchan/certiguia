# CertiGuia — orientação para certificado digital ICP-Brasil

Site público que guia profissionais na compra e uso de certificado digital (e-CPF/e-CNPJ, A1/A3). Inclui painel admin interno.

**Deploy na web:** veja [DEPLOY.md](DEPLOY.md) (Docker, Render ou Google Cloud Run).

## Desenvolvimento local
```
Cliente entra em contato (WhatsApp, telefone)
        ↓
Você cadastra no sistema (+ Novo cadastro)
        ↓
Envia cobrança ao cliente (WhatsApp automático)
        ↓
Confirma pagamento recebido
        ↓
Copia dados → Abre certificadora → Faz pedido A1/A3
        ↓
Registra nº do pedido → Acompanha validação/emissão
        ↓
Entrega certificado → Conclui serviço
```

## Instalação

```powershell
cd "C:\Users\ACER\Documents\Python Scripts\Qr_code"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Acesse: **http://localhost:5000**  
Senha padrão: `admin123`

## Funcionalidades

- **Cadastro interno** — todos os campos necessários para certificadora (CPF, RG, CRMV, endereço)
- **Precificação automática** — calcula valor de venda, custo e lucro (com desconto FABAHIA)
- **Fluxo guiado** — pipeline visual com botões de ação em cada etapa
- **Copiar dados** — gera texto pronto para colar no site da certificadora
- **Links diretos** — Certisign, Serasa, Valid, Safeweb
- **WhatsApp de cobrança** — mensagem pré-formatada para o cliente
- **Dashboard financeiro** — receita e lucro dos serviços pagos
- **Exportação CSV** — para controle/contabilidade

## Certificadoras configuradas

Edite preços e URLs em `certificado.py`:

| Certificadora | A1 (venda) | A3 (venda) |
|---------------|-----------|-----------|
| Certisign     | R$ 249    | R$ 399    |
| Serasa        | (mesmo link) | (mesmo link) |
| Valid         | (mesmo link) | (mesmo link) |
| Safeweb       | (mesmo link) | (mesmo link) |

Desconto FABAHIA: 15% no custo (vets da Bahia).

## Limitação importante

As certificadoras (Certisign, Serasa, etc.) **não possuem API pública** para compra automática. O app automatiza:

- Coleta e organização dos dados
- Cálculo de preços
- Geração do texto para copiar/colar
- Controle do fluxo e financeiro
- Cobrança via WhatsApp

O pedido na certificadora ainda é feito manualmente no site, mas com todos os dados prontos em um clique.
