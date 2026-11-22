"""Login com Google (nativo do Streamlit) e com e-mail e senha (Supabase Auth)."""

import streamlit as st
from supabase import create_client

from src import config

CHAVE_SESSAO = "usuario_email"

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


def google_configurado():
    """True se o login com Google estiver configurado em .streamlit/secrets.toml."""
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def email_configurado():
    """True se as chaves do Supabase estiverem no .env (ou nos Secrets da nuvem)."""
    return bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY and config.SUPABASE_SERVICE_KEY)


def usuario_atual():
    """Devolve {"email", "nome", "provedor"} de quem está logado, ou None."""
    if google_configurado() and st.user.is_logged_in:
        email = st.user.get("email", "")
        return {"email": email, "nome": st.user.get("name") or email, "provedor": "google"}

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

    st.session_state[CHAVE_SESSAO] = resposta.user.email
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


def sair():
    """Encerra a sessão, seja qual for a forma de login."""
    usuario = usuario_atual()
    st.session_state.pop(CHAVE_SESSAO, None)
    if usuario and usuario["provedor"] == "google":
        st.logout()
