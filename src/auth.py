"""Login com Google e GitHub (nativo do Streamlit) e com e-mail e senha (Supabase Auth)."""

import streamlit as st
from supabase import create_client

from src import config

CHAVE_SESSAO = "usuario_email"

# Login com e-mail lembrado entre visitas: o cookie guarda um token de sessão do
# Supabase (nunca a senha). O app grava e apaga o cookie em src/cookies.py.
NOME_COOKIE = "termo_sessao"
CHAVE_TOKEN = "token_sessao"            # token atual da sessão desta aba
CHAVE_SALVAR_COOKIE = "cookie_salvar"   # token novo que precisa ir para o cookie
CHAVE_APAGAR_COOKIE = "cookie_apagar"   # pedido para apagar o cookie
CHAVE_SAIU = "saiu_nesta_aba"           # impede restaurar o login depois de Sair

MENSAGENS_ERRO = {
    "invalid login credentials": "E-mail ou senha incorretos.",
    "email not confirmed": (
        "Confirme o seu e-mail antes de entrar. Procure a mensagem de confirmação "
        "na sua caixa de entrada (e no spam)."
    ),
    "user already registered": "Já existe uma conta com esse e-mail. Use a opção Entrar.",
    "rate limit": "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente de novo.",
    "expired or is invalid": "Código inválido ou expirado. Peça um código novo.",
    "should be different": "A nova senha precisa ser diferente da senha atual.",
}


def provedores_configurados():
    """Provedores de login configurados em .streamlit/secrets.toml.

    Aceita os dois formatos:
    - um provedor só: client_id direto dentro de [auth] (tratado como Google);
    - vários: [auth.google], [auth.github] etc.
    """
    try:
        bloco = st.secrets["auth"]
    except Exception:
        return set()

    if "client_id" in bloco:
        return {"google"}
    return {nome for nome in ("google", "github") if nome in bloco}


def google_configurado():
    return "google" in provedores_configurados()


def github_configurado():
    return "github" in provedores_configurados()


def entrar_com_provedor(provedor):
    """Abre o login do Google ou do GitHub (via Auth0)."""
    try:
        formato_simples = "client_id" in st.secrets["auth"]
    except Exception:
        formato_simples = False

    if formato_simples:
        st.login()
    else:
        st.login(provedor)


def provedor_do_login_externo(dados):
    """Descobre se o login externo veio do Google ou do GitHub (Auth0).

    Recebe os dados do login (o conteúdo de st.user) como dicionário.
    """
    emissor = str(dados.get("iss", ""))
    if "auth0.com" in emissor:
        return "github"
    return "google"


def normalizar_email(email):
    """Tira espaços e passa para minúsculas: Ana@Empresa.com e ana@empresa.com são o mesmo e-mail."""
    return (email or "").strip().lower()


def _email_verificado(dados):
    """True só quando o provedor confirma que o e-mail foi verificado."""
    valor = dados.get("email_verified")
    return valor is True or str(valor).lower() == "true"


def dono_do_login_externo(dados):
    """Decide quem é o dono dos leads num login com Google ou GitHub.

    - GitHub (via Auth0): usa sempre o identificador fixo da conta ("sub",
      no formato "github|12345"). Ele não muda e não pode ser escolhido por
      outra pessoa, ao contrário do e-mail.
    - Google: usa o e-mail, mas só se o Google confirmar que ele foi verificado.

    Devolve None quando não dá para confiar na identidade. Nesse caso,
    o app não mostra leads de ninguém.
    """
    if provedor_do_login_externo(dados) == "github":
        sub = str(dados.get("sub") or "").strip()
        if sub.startswith("github|"):
            return sub
        return None

    email = normalizar_email(dados.get("email"))
    if email and _email_verificado(dados):
        return email
    return None


def email_configurado():
    """True se as chaves do Supabase estiverem no .env (ou nos Secrets da nuvem)."""
    return bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY and config.SUPABASE_SERVICE_KEY)


def login_externo_ativo():
    """True se a pessoa entrou com Google ou GitHub (mesmo que a identidade seja recusada)."""
    return bool(provedores_configurados()) and st.user.is_logged_in


def usuario_atual():
    """Devolve os dados de quem está logado, ou None.

    "dono" é a chave que separa os leads de cada conta no banco.
    "email" e "nome" servem só para mostrar na tela.
    """
    if login_externo_ativo():
        campos = ("iss", "sub", "email", "email_verified", "name", "nickname")
        dados = {campo: st.user.get(campo) for campo in campos}
        dono = dono_do_login_externo(dados)
        if dono is None:
            return None
        email = normalizar_email(dados.get("email"))
        nome = dados.get("name") or dados.get("nickname") or email or "Usuário"
        return {
            "dono": dono,
            "email": email,
            "nome": nome,
            "provedor": provedor_do_login_externo(dados),
        }

    email = st.session_state.get(CHAVE_SESSAO)
    if email:
        return {"dono": email, "email": email, "nome": email, "provedor": "email"}

    return None


def validar_credenciais(email, senha):
    """Confere o formato do e-mail e o tamanho da senha. Devolve uma lista de erros."""
    erros = []
    email = email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        erros.append("Informe um e-mail válido.")
    if len(senha) < 6:
        erros.append("A senha precisa ter pelo menos 6 caracteres.")
    return erros


def traduzir_erro(erro):
    """Transforma o erro do Supabase em uma mensagem clara, em português."""
    texto = str(erro).lower()
    for trecho, mensagem in MENSAGENS_ERRO.items():
        if trecho in texto:
            return mensagem
    if "password" in texto:
        return "Senha recusada. Use pelo menos 6 caracteres."
    return "Não foi possível concluir agora. Tente novamente em instantes."


def _cliente_auth():
    """Conexão com o Supabase usando a chave pública, só para login e cadastro."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)


def entrar_com_email(email, senha):
    """Faz login com e-mail e senha. Devolve (sucesso, mensagem)."""
    try:
        resposta = _cliente_auth().auth.sign_in_with_password(
            {"email": email.strip(), "password": senha}
        )
    except Exception as erro:
        return False, traduzir_erro(erro)

    _guardar_sessao(resposta)
    return True, ""


def criar_conta(email, senha):
    """Cria uma conta com e-mail e senha. Devolve (sucesso, mensagem)."""
    try:
        _cliente_auth().auth.sign_up({"email": email.strip(), "password": senha})
    except Exception as erro:
        return False, traduzir_erro(erro)

    return True, (
        "Conta criada. Enviamos um link de confirmação para o seu e-mail. "
        "Depois de confirmar, volte aqui e entre."
    )


def enviar_codigo_recuperacao(email):
    """Pede ao Supabase um e-mail com o código para redefinir a senha."""
    try:
        _cliente_auth().auth.reset_password_for_email(email.strip())
    except Exception as erro:
        return False, traduzir_erro(erro)

    return True, (
        "Se existir uma conta com esse e-mail, enviamos um código para redefinir a senha. "
        "Confira a caixa de entrada e o spam."
    )


def redefinir_senha(email, codigo, nova_senha):
    """Confere o código do e-mail e grava a nova senha. Devolve (sucesso, mensagem)."""
    cliente = _cliente_auth()
    try:
        cliente.auth.verify_otp({"email": email.strip(), "token": codigo.strip(), "type": "recovery"})
        cliente.auth.update_user({"password": nova_senha})
    except Exception as erro:
        return False, traduzir_erro(erro)

    return True, "Senha alterada. Agora é só entrar com a nova senha."


def _guardar_sessao(resposta):
    """Guarda o e-mail na aba e pede para salvar o token no cookie."""
    st.session_state[CHAVE_SESSAO] = normalizar_email(resposta.user.email)
    st.session_state.pop(CHAVE_SAIU, None)
    if resposta.session is not None:
        st.session_state[CHAVE_TOKEN] = resposta.session.refresh_token
        st.session_state[CHAVE_SALVAR_COOKIE] = resposta.session.refresh_token


def token_do_cookie(cookies):
    """Devolve o token salvo no cookie, ou None. Recebe um dicionário de cookies."""
    token = (cookies or {}).get(NOME_COOKIE, "")
    return token.strip() or None


def restaurar_sessao(cookies):
    """Se houver um token válido no cookie, entra de novo sem pedir a senha.

    Roda no início de cada visita. O Supabase troca o token a cada uso,
    então o token novo é salvo no cookie no lugar do antigo.
    """
    if st.session_state.get(CHAVE_SESSAO) or st.session_state.get(CHAVE_SAIU):
        return
    if not email_configurado():
        return

    token = token_do_cookie(cookies)
    if token is None:
        return

    try:
        resposta = _cliente_auth().auth.refresh_session(token)
    except Exception:
        st.session_state[CHAVE_APAGAR_COOKIE] = True
        return

    if resposta.user is None:
        st.session_state[CHAVE_APAGAR_COOKIE] = True
        return

    _guardar_sessao(resposta)


def _encerrar_sessao_no_supabase():
    """Invalida o token no Supabase, para o cookie não servir mais para nada."""
    token = st.session_state.get(CHAVE_TOKEN)
    if not token:
        return
    try:
        cliente = _cliente_auth()
        cliente.auth.refresh_session(token)
        cliente.auth.sign_out()
    except Exception:
        pass


def sair():
    """Encerra a sessão, seja qual for a forma de login."""
    usuario = usuario_atual()
    externo = login_externo_ativo()

    if usuario and usuario["provedor"] == "email":
        _encerrar_sessao_no_supabase()

    st.session_state.pop(CHAVE_SESSAO, None)
    st.session_state.pop(CHAVE_TOKEN, None)
    st.session_state.pop(CHAVE_SALVAR_COOKIE, None)
    st.session_state[CHAVE_APAGAR_COOKIE] = True
    st.session_state[CHAVE_SAIU] = True

    # Também sai quando o login externo foi recusado (usuario é None nesse caso)
    if externo:
        st.logout()
