---
formato: a3-token
atualizado: 2026-06-09
---

## Instalar e-CPF A3 com token USB

**Não funciona no celular** — use token só em computadores com porta USB.

### 1. Driver e token

1. Instale o driver do token (SafeNet, GD, etc.) — link vem no e-mail da certificadora.
2. Conecte o token USB e aguarde o Windows reconhecer.

### 2. Verificar certificado

Abra `certmgr.msc` → **Pessoal** → **Certificados** e confirme que o e-CPF A3 aparece.

### 3. Configurar no software

Em **Certificado digital**, selecione **A3**, **Token** ou **Dispositivo criptográfico** e escolha o token quando pedir PIN.

### 4. Testar

Assine um documento de teste e valide em [validar.iti.gov.br](https://validar.iti.gov.br/).
