---
software: projuris
software_nome: Projuris
profissao: advogado
formato: a1-arquivo
atualizado: 2026-06-10
fonte: automacao
fonte_url: https://projurisadv.atlassian.net/wiki/spaces/BDC/pages/4369874957/Cofre+de+Certificados+Digitais+como+cadastrar+e+vincular+certificados+no+Projuris+ADV
---

## Projuris — a1 arquivo

Guia gerado automaticamente a partir da documentação oficial. Revise os passos antes de publicar em produção.

**Fonte:** [Cofre de Certificados Digitais: como cadastrar e vincular certificados no Projuris ADV - Central de Ajuda - Projuris ADV - Confluence](https://projurisadv.atlassian.net/wiki/spaces/BDC/pages/4369874957/Cofre+de+Certificados+Digitais+como+cadastrar+e+vincular+certificados+no+Projuris+ADV)

### Passos (extraídos da documentação)

Cofre de Certificados Digitais: como cadastrar e vincular certificados no Projuris ADV
By Lara Gonzalez de Souza (Unlicensed)
4 min
Add a reaction
Com o Cofre de Certificados Digitais, agora é possível cadastrar certificados do tipo A1 (.pfx) diretamente na plataforma e vinculá-los às credenciais utilizadas para capturas de intimações e processos.
Essa funcionalidade oferece mais autonomia e agilidade, especialmente nos casos em que tribunais exigem autenticação por certificado digital, como os sistemas EPROC e JUD RJ.
O que é o Cofre de Certificados Digitais?
É um espaço seguro dentro do Projuris ADV onde os usuários podem armazenar seus certificados digitais tipo A1 e utilizá-los em conjunto com as credenciais cadastradas no cofre de senhas.
Assim, não é mais necessário abrir um chamado para enviar o certificado manualmente: o próprio usuário pode configurar e gerenciar os certificados diretamente pelo sistema.
Onde acessar o Cofre de Certificados?
Você pode acessar o Cofre de Certificados Digitais diretamente pelo módulo de Intimações. Para isso, siga os passos:
Acesse o módulo Processos no menu lateral do Projuris ADV
Clique em Intimações
No canto superior direito da tela, clique no ícone de engrenagem
Selecione a opção Cofre de certificados
Open
Open
Como cadastrar um novo certificado?
Acesse o Cofre de Certificados e clique em Novo Certificado
Na janela que abrir, preencha os seguintes campos:
Arquivo .pfx: selecione ou arraste o arquivo do certificado
PIN do certificado: insira a senha de acesso do .pfx
Credenciais: selecione os logins dos tribunais aos quais o certificado será vinculado. É possível selecionar múltiplas credenciais.
Marque a opção de aceite dos termos de uso do Cofre de Senhas.
Clique em Salvar.
Open
🟢 Se tudo estiver correto, o sistema exibirá:
"Certificado digital cadastrado."
❌ Em caso de erro:
Formato ou validade incorreta: "Certificado digital inválido."
PIN errado: "PIN do certificado digital incorreto."
Importante: selecione as credenciais para vinculação!
Para que o certificado digital cadastrado seja efetivamente utilizado para login no tribunal, é obrigatório selecionar quais credenciais (tribunais) ele irá atender no momento do cadastro.
💡 Exemplo:
Usuário possui credenciais do TJSP, TJSC e TJPR.
Ao cadastrar o certificado, ele seleciona apenas o TJSP.
👉 Nesse caso, o sistema utilizará o certificado apenas para login no TJSP.
Caso deseje usar o mesmo certificado para vários tribunais, basta selecionar múltiplas credenciais no momento do cadastro.
A vinculação de um mesmo certificado a diferentes tribunais deve ser feita no momento do cadastro do certificado. Após esse passo, será necessário acessar cada senha cadastrada no Cofre de Senhas e editar individualmente para concluir a vinculação do certificado às credenciais correspondentes.
Como vincular um certificado a uma credencial?
Você também pode fazer essa vinculação ao cadastrar ou editar uma senha no Cofre de Senhas:
Durante o cadastro de uma nova senha:
Acesse Configurações de captura > Cofre de senhas;
Clique em Nova senha;
Preencha os campos obrigatórios (órgão, sistema, login, senha);
No campo Vincular certificado, selecione o certificado desejado.
Open
Durante a edição de uma senha existente:
Clique no ícone de edição na credencial desejada;
No campo Vincular certificado, selecione um certificado válido.
Open
Open
⚠️ Importante: para sistemas como JUD RJ, o vínculo com o certificado será obrigatório.
Como excluir um certificado digital?
Acesse o Cofre de certificados;
Clique no botão de ações (três pontos) ao lado do certificado;
Selecione Excluir certificado.
Será exibida uma mensagem de alerta informando que a exclusão pode impactar capturas em andamento. A exclusão é definitiva e só pode ser feita pelo administrador do sistema ou usuário que cadastrou o certificado.
Open
Dicas úteis:
Certificados podem ser usados para várias credenciais;
Use nomes claros nos arquivos para facilitar a identificação (ex: joao_adv_2025.pfx);
O sistema informa quando o certificado está vencido ou sem uso (sem credenciais vinculadas);
Cada certificado fica protegido no Cofre de Senhas, com segurança e criptografia.
Ficou com dúvidas?
Se ainda tiver dúvidas sobre como utilizar o Cofre de Certificados Digitais, fale com o nosso time de suporte:
Chat: acesse o chat no canto inferior direito do Projuris ADV
WhatsApp: (48) 99146-6932 – segunda à sexta, das 9h às 18h.
Estamos prontos para te ajudar!💚
View all comments
Open Details Panel
Open Rovo Chat
Add a comment
Add a reaction
Projuris ADV powered by Softplan
www.projuris.com.br/adv
