---
software: prescreve
software_nome: Prescreve / VetPrescriber
profissao: veterinario
formato: a3-nuvem
atualizado: 2026-06-09
fonte: manual
---

## Configurar e-CPF A3 nuvem no Prescreve

Para receituário veterinário no **celular** e no **computador** com certificado **A3 nuvem (HSM)**.

### Pré-requisitos

- e-CPF A3 nuvem ativo na certificadora.
- App da certificadora no celular (Valid Credentials, Certisign mobileID, etc.).

### No Prescreve (celular — comum)

1. Abra o app **Prescreve** / **VetPrescriber**.
2. Menu **Configurações** → **Certificado digital** ou **Assinatura ICP-Brasil**.
3. Selecione **Nuvem**, **HSM** ou integração com app da certificadora.
4. Faça login com CPF e autorize no app da AC.
5. Emita receita de teste e confira QR Code / selo ICP-Brasil.

### No Prescreve (web/desktop)

1. Acesse o painel web ou versão desktop.
2. **Configurações** → **Certificado** → **A3 nuvem**.
3. Autentique quando o middleware da certificadora abrir.

### Testar

Valide o PDF da receita em [validar.iti.gov.br](https://validar.iti.gov.br/).
