"""Login com Google (nativo do Streamlit) e com e-mail e senha (Supabase Auth)."""

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


def _provedor_do_login_externo():
    """Descobre se o login externo veio do Google ou do GitHub (Auth0)."""
    emissor = str(st.user.get("iss", ""))
    if "auth0.com" in emissor:
        return "github"
    return "google"


def email_configurado():
    """True se as chaves do Supabase estiverem no .env (ou nos Secrets da nuvem)."""
    return bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY and config.SUPABASE_SERVICE_KEY)


def usuario_atual():
    """Devolve {"email", "nome", "provedor"} de quem está logado, ou None."""
    if provedores_configurados() and st.user.is_logged_in:
        # O GitHub pode não informar o e-mail (quando ele é privado). Nesse caso,
        # o identificador fixo da conta ("sub") separa os leads desse usuário.
        email = st.user.get("email") or st.user.get("sub", "")
        nome = st.user.get("name") or st.user.get("nickname") or email
        return {"email": email, "nome": nome, "provedor": _provedor_do_login_externo()}

    email = st.session_state.get(CHAVE_SESSAO)
    if email:
        return {"email": email, "nome": email, "provedor": "email"}

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
    st.session_state[CHAVE_SESSAO] = resposta.user.email
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

    if usuario and usuario["provedor"] == "email":
        _encerrar_sessao_no_supabase()

    st.session_state.pop(CHAVE_SESSAO, None)
    st.session_state.pop(CHAVE_TOKEN, None)
    st.session_state.pop(CHAVE_SALVAR_COOKIE, None)
    st.session_state[CHAVE_APAGAR_COOKIE] = True
    st.session_state[CHAVE_SAIU] = True

    if usuario and usuario["provedor"] in ("google", "github"):
        st.logout()
