# Deploy do CertiGuia na web

Guia para colocar o CertiGuia no ar com **Docker**, no **Render** (mais simples) ou no **Google Cloud Run** (mais escalável).

---

## O que você precisa

| Item | Obrigatório? | Onde conseguir |
|------|--------------|----------------|
| Domínio (ex.: `certiguia.com.br`) | Recomendado | [Registro.br](https://registro.br) ou Google Cloud Domains |
| Hospedagem na nuvem | Sim | Render ou Google Cloud |
| Banco PostgreSQL | Sim em produção | Incluso no Render / Cloud SQL no GCP |
| Conta Git (GitHub) | Sim | Para enviar o código |

**Não precisa** de operadora de hospedagem tradicional (Hostinger, Locaweb etc.) — a nuvem **é** a hospedagem.

---

## Variáveis de ambiente

Copie `.env.example` para `.env` localmente. Na nuvem, configure:

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave aleatória longa (sessões Flask) |
| `ADMIN_PASSWORD` | Senha do painel `/admin` |
| `DATABASE_URL` | PostgreSQL em produção (`postgresql://...`) |
| `WHATSAPP_SUPORTE` | Número com DDI (ex.: `5571987939074`) |
| `PIX_CHAVE`, `PIX_NOME`, `PIX_CIDADE` | Doação via Pix |
| `GUNICORN_TIMEOUT` | Opcional; padrão `120` (busca de preços) |

Gere uma `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testar com Docker no seu PC

Pré-requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado.

```powershell
cd "C:\Users\ACER\Documents\Python Scripts\Qr_code"
copy .env.example .env
# Edite .env com suas chaves

docker build -t certiguia .
docker run --rm -p 8080:8080 --env-file .env certiguia
```

Abra: **http://localhost:8080**  
Health check: **http://localhost:8080/health**

Com PostgreSQL local (docker-compose):

```powershell
docker compose up --build
# DATABASE_URL=postgresql://certiguia:certiguia@db:5432/certiguia
```

---

## Opção A — Render (recomendado para começar)

Mais rápido de configurar; plano gratuito disponível (com limitações).

### 1. Enviar código para o GitHub

```powershell
git init
git add .
git commit -m "CertiGuia pronto para deploy"
git remote add origin https://github.com/SEU_USUARIO/certiguia.git
git push -u origin main
```

### 2. Criar conta no Render

1. Acesse [render.com](https://render.com) e conecte o GitHub.
2. **New → Blueprint** e selecione o repositório (usa o `render.yaml`), **ou** configure manualmente:

### 3. Deploy manual no Render

1. **New → Web Service** → repositório → **Runtime: Docker**.
2. **New → PostgreSQL** → copie a **Internal Database URL**.
3. No Web Service, **Environment**:

   - `DATABASE_URL` = URL do Postgres (Render converte `postgres://` automaticamente)
   - `SECRET_KEY`, `ADMIN_PASSWORD`, `PIX_*`, `WHATSAPP_SUPORTE`

4. **Advanced**:
   - Health Check Path: `/health`
   - Instance type: pelo menos **Starter** (Playwright precisa de RAM)

5. **Create Web Service** — o primeiro build leva ~5–10 min (imagem com Chromium).

### 4. Domínio no Render

- **Settings → Custom Domains** → adicione `certiguia.com.br`.
- No Registro.br (ou onde comprou o domínio), crie um **CNAME** apontando para o endereço que o Render informar.

---

## Opção B — Google Cloud Run

Melhor para escalar; exige mais passos.

### Pré-requisitos

- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) instalado
- Projeto GCP criado e billing ativado

```powershell
gcloud auth login
gcloud config set project SEU_PROJETO_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com sqladmin.googleapis.com
```

### 1. Banco Cloud SQL (PostgreSQL)

```powershell
gcloud sql instances create certiguia-db `
  --database-version=POSTGRES_16 `
  --tier=db-f1-micro `
  --region=southamerica-east1

gcloud sql databases create certiguia --instance=certiguia-db
gcloud sql users create certiguia --instance=certiguia-db --password=SUA_SENHA_FORTE
```

Anote: `postgresql://certiguia:SUA_SENHA@/certiguia?host=/cloudsql/PROJETO:southamerica-east1:certiguia-db`  
(ou use IP público do Cloud SQL se preferir conexão direta)

### 2. Build e deploy

```powershell
cd "C:\Users\ACER\Documents\Python Scripts\Qr_code"

gcloud artifacts repositories create certiguia `
  --repository-format=docker `
  --location=southamerica-east1

gcloud builds submit --tag southamerica-east1-docker.pkg.dev/SEU_PROJETO_ID/certiguia/app:latest

gcloud run deploy certiguia `
  --image southamerica-east1-docker.pkg.dev/SEU_PROJETO_ID/certiguia/app:latest `
  --region southamerica-east1 `
  --platform managed `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars "SECRET_KEY=SUA_SECRET,ADMIN_PASSWORD=SUA_SENHA,CERTIFICADORA_PADRAO=certisign" `
  --set-env-vars "WHATSAPP_SUPORTE=5571987939074,PIX_CHAVE=sua-chave,PIX_NOME=SEU NOME,PIX_CIDADE=SALVADOR" `
  --set-env-vars "DATABASE_URL=postgresql://certiguia:SENHA@HOST:5432/certiguia"
```

Ajuste memória (`2Gi`) e timeout (`300`) — a busca de preços com Playwright precisa disso.

### 3. Domínio no Cloud Run

1. **Cloud Run → certiguia → Manage custom domains**
2. Verifique o domínio no Google
3. No Registro.br, aponte **CNAME** ou **A** conforme instruções do GCP

### 4. Domínio (.com.br)

- [Registro.br](https://registro.br): ~R$ 40/ano para `.com.br`
- Google Cloud Domains: integrado ao GCP, preço similar

---

## Checklist pós-deploy

- [ ] Acessar `/` — página inicial carrega
- [ ] `/health` retorna `{"status":"ok","playwright":true}`
- [ ] Cadastro em `/comecar` salva no banco
- [ ] Painel `/admin` com senha forte (não deixe `admin123`)
- [ ] Buscar preços funciona (pode demorar na 1ª vez)
- [ ] HTTPS ativo (Render/GCP fazem automaticamente)
- [ ] Pix de doação testado

---

## Custos estimados (ordem de grandeza)

| Plataforma | Uso leve | Observação |
|------------|----------|------------|
| Render Free | R$ 0 | Postgres free expira em 90 dias; web free dorme |
| Render Starter | ~US$ 7/mês + DB | Recomendado para uso real |
| Cloud Run | ~US$ 5–20/mês | Paga por uso; + Cloud SQL ~US$ 10/mês |

---

## Problemas comuns

**Playwright false no `/health`**  
Imagem Docker errada ou build sem Chromium. Use o `Dockerfile` deste repositório.

**Busca de preços timeout**  
Aumente `GUNICORN_TIMEOUT` e o timeout do Cloud Run (300s).

**Dados sumiram após redeploy**  
SQLite em container não persiste. Use `DATABASE_URL` com PostgreSQL.

**Erro de memória (OOM)**  
Suba para 2 GB RAM no Render/Cloud Run.

---

## Estrutura de arquivos de deploy

```
Dockerfile              # Imagem com Python + Chromium
docker-entrypoint.sh    # Gunicorn na porta PORT
docker-compose.yml      # Teste local + Postgres opcional
render.yaml             # Blueprint Render
DEPLOY.md               # Este guia
```
