# Política de privacidade do Termo

Última atualização: 22 de novembro de 2026.

O Termo é um projeto de portfólio de Vinícius Abreu Queiroz Felicio, estudante da Universidade Federal de Uberlândia. É um qualificador de leads publicado em https://termo-leads.streamlit.app, sem fins comerciais. Esta página explica quais dados o app guarda, para que servem e como pedir a exclusão.

## Dados coletados

Quem entra com a conta Google compartilha o nome e o endereço de e-mail da conta. O app não recebe a senha do Google nem outros dados do perfil.

Quem cria conta com e-mail e senha informa o endereço de e-mail e uma senha. A senha é guardada pelo Supabase em formato criptografado (hash). O app nunca tem acesso à senha em texto.

Os leads cadastrados por um usuário logado (empresa, contato, segmento, necessidade, descrição, orçamento, prazo e resultado da qualificação) ficam guardados junto com o e-mail de quem os cadastrou.

Os visitantes que não entram em nenhuma conta usam uma base de demonstração com dados fictícios, que volta ao estado inicial quando o app reinicia.

## Como os dados são usados

O e-mail identifica a conta e separa os leads de cada usuário. Ele também é usado para enviar a confirmação de cadastro e o código de recuperação de senha. O app não envia outros e-mails, não vende dados e não os compartilha para publicidade.

## Serviços de terceiros

- Supabase: guarda as contas de e-mail e os leads dos usuários logados, em servidores na região de São Paulo.
- Google: faz o login com conta Google e, pela API do Gemini, gera a análise complementar de cada lead cadastrado. Na camada gratuita da API, o conteúdo enviado pode ser usado pelo Google para melhorar os produtos dele. Por isso o app pede que não sejam cadastrados dados reais.
- Streamlit Community Cloud: hospeda o app.
- Gmail: envia os e-mails de confirmação e de recuperação de senha.

## Cookies

Quem entra com a conta Google recebe um cookie de sessão, que mantém o login ativo por até 30 dias ou até a pessoa clicar em Sair. O app não usa cookies de publicidade ou de rastreamento.

## Exclusão de dados

Para apagar a conta e todos os leads associados, abra uma issue no repositório do projeto: https://github.com/viniciusab12/qualificador-leads/issues. Os leads também podem ser apagados um a um, a qualquer momento, na página Leads do app.

## Alterações

Esta política pode mudar conforme o projeto evolui. A data no topo indica a versão em vigor.
