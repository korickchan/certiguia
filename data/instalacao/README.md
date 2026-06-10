# Guias de instalação por software

Este diretório alimenta a etapa **Instalação** da jornada do CertiGuia, depois que o usuário escolhe certificadora e software.

## Estrutura

```
data/instalacao/
  index.json              # catálogo: profissões → softwares → formatos suportados
  README.md               # este arquivo
  _generico/              # fallback quando não há guia específico
    a1-arquivo.md
    a3-nuvem.md
    ...
  {profissao}/
    {software_id}/
      {formato}.md        # ex.: advogado/projuris/a3-nuvem.md
```

## Chaves de formato (`formato`)

Devem coincidir com as chaves em `index.json` → `formatos`:

| Chave | Quando usar |
|-------|-------------|
| `a1-arquivo` | A1 .pfx no Windows/macOS |
| `a1-mobileid` | A1 MobileID no celular |
| `a1-nuvem` | A1 HSM (raro) |
| `a3-nuvem` | A3 nuvem — PC e celular |
| `a3-token` | A3 token USB |
| `a3-cartao` | A3 cartão + leitora |
| `a3-sem-midia` | A3 renovação sem mídia nova |

O site deriva a chave automaticamente de `armazenamento` + `preferencia_midia` do usuário.

## Formato do arquivo `.md`

Use frontmatter YAML opcional + corpo Markdown:

```markdown
---
software: projuris
software_nome: Projuris
profissao: advogado
formato: a3-nuvem
atualizado: 2026-06-09
fonte: manual
---

## Pré-requisitos

- Certificado e-CPF A3 em nuvem já emitido pela certificadora escolhida.

## Passos no Projuris

1. Acesse **Configurações → Certificado digital**.
2. ...
```

Campos úteis no frontmatter (todos opcionais):

- `software`, `software_nome`, `profissao`, `formato`
- `atualizado` (ISO date)
- `fonte` (`manual`, `automacao`, URL)
- `certificadoras` (lista de slugs se o passo for específico de AC)

## Automação (inserir novos guias)

1. Adicione ou atualize o software em `index.json` → `profissoes.{prof}.softwares[]`.
2. Crie `data/instalacao/{profissao}/{software_id}/{formato}.md`.
3. Se faltar guia específico, o site usa `_generico/{formato}.md`.
4. Reinicie o app (ou aguarde reload) — não precisa migrar banco.

### Exemplo de script (pseudo)

```python
from pathlib import Path

def salvar_guia(profissao, software_id, formato, markdown: str):
    path = Path("data/instalacao") / profissao / software_id / f"{formato}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
```

## Profissões no index

`advogado`, `veterinario`, `medico`, `dentista`, `contador`, `farmaceutico`, `outro`

Use `outro` como software genérico quando não houver guia dedicado.

## Principais SaaS por ramo (catálogo)

| Profissão | Softwares no picker |
|-----------|---------------------|
| Advogado | Projuris, Astrea, CPJ-3C, Legal One, ADVBox, eJus |
| Veterinário | Prescreve, **Simples Vet**, VetSoft, OneVet, Smart Vet |
| Médico | Memed, iClinic, Amplimed, Shosp, Doctoralia |
| Dentista | Simples Dental, Clinicorp, Dental Office, DentalPro |
| Contador | Domínio, Alterdata, Conta Azul, FortCont, Omie, SCI |
| Farmacêutico | Trier, Prisma/FarmaFácil, Sofista, Hiper |
| Outra profissão | **Dietbox** (nutricionista), Navegador/Gov.br, Outro |

Campo `fontes` em cada software (quando preenchido) alimenta `scripts/varredura_instalacao.py`.

```bash
python scripts/varredura_instalacao.py --profissao veterinario --software simples_vet
python scripts/varredura_instalacao.py --dry-run
```
