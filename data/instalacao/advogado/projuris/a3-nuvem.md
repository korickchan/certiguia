---
software: projuris
software_nome: Projuris
profissao: advogado
formato: a3-nuvem
atualizado: 2026-06-09
fonte: manual
---

## Configurar e-CPF A3 nuvem no Projuris

Certificado **A3 em nuvem (HSM)** — funciona no escritório (Windows) e no celular. **Não** use token USB neste fluxo.

### Pré-requisitos

- e-CPF A3 nuvem emitido e ativo na certificadora escolhida.
- App da certificadora instalado no celular, se for assinar pelo smartphone.
- Projuris atualizado (cloud ou desktop conforme sua licença).

### No Projuris Desktop (Windows)

1. Abra o **Projuris** e acesse **Configurações** (ícone de engrenagem).
2. Vá em **Certificado digital** ou **Assinatura eletrônica**.
3. Selecione **Certificado em nuvem**, **HSM** ou **Remote ID** (a nomenclatura pode variar).
4. Escolha a certificadora emissora e informe CPF.
5. Quando solicitado, autentique no popup ou app da AC (PIN/senha/biometria).
6. Marque o certificado como padrão para petições e documentos.

### No celular (Projuris app / navegador)

1. No app Projuris ou portal web móvel, abra **Assinatura** / **Certificado**.
2. Escolha **Nuvem (HSM)** — não selecione arquivo `.pfx` nem token.
3. Autorize no app da certificadora quando aparecer a notificação.

### Testar

1. Assine uma petição ou minuta de teste.
2. Exporte o PDF e valide em [validar.iti.gov.br](https://validar.iti.gov.br/).

### Observações

- Se só aparecer opção **A1 arquivo** ou **Token A3**, confira se comprou **A3 nuvem** e não outro produto.
- Dúvidas específicas da AC: use o suporte da certificadora escolhida no guia de compra acima.
