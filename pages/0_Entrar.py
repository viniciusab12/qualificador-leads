import streamlit as st

from src.auth import (
    SENHA_MINIMA,
    criar_conta,
    email_configurado,
    entrar_com_email,
    entrar_com_provedor,
    enviar_codigo_recuperacao,
    github_configurado,
    google_configurado,
    redefinir_senha,
    usuario_atual,
    validar_credenciais,
)

LOGO_BRANCO = (
    '<svg width="30" height="30" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="18" y="5" width="12" height="28" rx="6" fill="none" stroke="#fff" stroke-width="3"/>'
    '<circle cx="24" cy="36" r="8" fill="#fff"/>'
    '<rect x="22" y="15" width="4" height="20" rx="2" fill="#fff"/>'
    '<line x1="33" y1="12" x2="37" y2="12" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>'
    '<line x1="33" y1="19" x2="37" y2="19" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>'
    '<line x1="33" y1="26" x2="37" y2="26" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>'
    "</svg>"
)

TEXTOS = {
    "entrar": {
        "titulo": "Entrar",
        "subtitulo": "Acesse seus leads e o dashboard.",
        "botao": "Entrar",
        "link": "Não tem conta? Criar conta",
        "outro_modo": "criar",
    },
    "criar": {
        "titulo": "Criar conta",
        "subtitulo": "Use um e-mail válido e uma senha com pelo menos 8 caracteres.",
        "botao": "Criar conta",
        "link": "Já tem conta? Entrar",
        "outro_modo": "entrar",
    },
    "recuperar": {
        "titulo": "Recuperar senha",
        "subtitulo": "Informe o seu e-mail para receber um código e criar uma senha nova.",
        "botao": "Enviar código",
        "link": "Voltar para Entrar",
        "outro_modo": "entrar",
    },
}


def trocar_modo(novo_modo):
    st.session_state["modo_login"] = novo_modo
    st.session_state.pop("email_recuperacao", None)


def processar_login(modo):
    """Roda no clique do botão, antes de a página recarregar.

    Assim, quando a página recarrega, o app já sabe que a pessoa entrou
    e mostra o menu de usuário logado na primeira tentativa.
    """
    email = st.session_state.get("login_email", "")
    senha = st.session_state.get("login_senha", "")
    # A senha sai da memória da sessão logo depois de ser lida
    st.session_state["login_senha"] = ""

    erros = validar_credenciais(email, senha, senha_nova=(modo == "criar"))
    if erros:
        st.session_state["login_erros"] = erros
        return

    if modo == "entrar":
        sucesso, mensagem = entrar_com_email(email, senha)
    else:
        sucesso, mensagem = criar_conta(email, senha)

    if sucesso and modo == "criar":
        st.session_state["login_sucesso"] = mensagem
    elif not sucesso:
        st.session_state["login_erros"] = [mensagem]


def formulario_recuperacao():
    """Etapa 1: pedir o código. Etapa 2: informar o código e a nova senha."""
    email_salvo = st.session_state.get("email_recuperacao")

    if not email_salvo:
        with st.form("form_recuperar", border=False):
            email = st.text_input("E-mail", placeholder="voce@email.com")
            enviado = st.form_submit_button("Enviar código", type="primary", width="stretch")

        if enviado:
            erros = validar_credenciais(email, "senha_ficticia")
            if erros:
                st.error(erros[0])
                return
            sucesso, mensagem = enviar_codigo_recuperacao(email)
            if sucesso:
                st.session_state["email_recuperacao"] = email.strip()
                st.rerun()
            else:
                st.error(mensagem)
        return

    st.success(f"Código enviado para {email_salvo}, se houver uma conta com esse e-mail.")
    with st.form("form_nova_senha", border=False):
        codigo = st.text_input("Código recebido por e-mail")
        nova_senha = st.text_input(
            "Nova senha", type="password", placeholder=f"Mínimo de {SENHA_MINIMA} caracteres"
        )
        enviado = st.form_submit_button("Salvar nova senha", type="primary", width="stretch")

    if enviado:
        erros = validar_credenciais(email_salvo, nova_senha)
        if not codigo.strip():
            erros.insert(0, "Informe o código recebido por e-mail.")
        if erros:
            for erro in erros:
                st.error(erro)
            return
        sucesso, mensagem = redefinir_senha(email_salvo, codigo, nova_senha)
        if sucesso:
            st.session_state["modo_login"] = "entrar"
            st.session_state.pop("email_recuperacao", None)
            st.session_state["aviso_login"] = mensagem
            st.rerun()
        else:
            st.error(mensagem)


# Quem já entrou não precisa ver esta tela
if usuario_atual():
    st.switch_page("inicio.py")

# Fundo branco e cartão centralizado na vertical, só nesta página
st.html(
    """<style>
    [data-testid="stAppViewContainer"] { background: #ffffff; }
    [data-testid="stMainBlockContainer"] {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }
    .st-key-cartao_login { margin-top: 0; }
    </style>"""
)

modo = st.session_state.setdefault("modo_login", "entrar")
textos = TEXTOS[modo]

_, centro, _ = st.columns([1, 1.15, 1])

with centro:
    with st.container(key="cartao_login"):
        st.markdown(f'<div class="login-logo">{LOGO_BRANCO}Termo</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="login-titulo">{textos["titulo"]}</div>'
            f'<div class="login-sub">{textos["subtitulo"]}</div>',
            unsafe_allow_html=True,
        )

        if "aviso_login" in st.session_state:
            st.success(st.session_state.pop("aviso_login"))

        if modo == "recuperar" and email_configurado():
            formulario_recuperacao()
        elif email_configurado():
            for erro in st.session_state.pop("login_erros", []):
                st.error(erro)
            if "login_sucesso" in st.session_state:
                st.success(st.session_state.pop("login_sucesso"))

            with st.form("form_login", border=False):
                st.text_input("E-mail", placeholder="voce@email.com", key="login_email")
                st.text_input(
                    "Senha",
                    type="password",
                    placeholder=f"Mínimo de {SENHA_MINIMA} caracteres" if modo == "criar" else "Sua senha",
                    key="login_senha",
                )
                st.form_submit_button(
                    textos["botao"],
                    type="primary",
                    width="stretch",
                    on_click=processar_login,
                    args=(modo,),
                )
            if modo == "entrar":
                st.button(
                    "Esqueceu a senha?",
                    key="link_esqueci",
                    type="tertiary",
                    on_click=trocar_modo,
                    args=("recuperar",),
                )
        else:
            st.info("Login com e-mail indisponível: as chaves do Supabase não estão configuradas.")

        st.markdown('<div class="login-ou">ou continue com</div>', unsafe_allow_html=True)

        coluna_google, coluna_github = st.columns(2)
        with coluna_google:
            st.button(
                "Google",
                key="btn_google",
                on_click=entrar_com_provedor,
                args=("google",),
                disabled=not google_configurado(),
                width="stretch",
            )
        with coluna_github:
            st.button(
                "GitHub",
                key="btn_github",
                on_click=entrar_com_provedor,
                args=("github",),
                disabled=not github_configurado(),
                help=None if github_configurado() else "Login com GitHub em breve.",
                width="stretch",
            )

        st.button(
            textos["link"],
            key="link_modo",
            type="tertiary",
            on_click=trocar_modo,
            args=(textos["outro_modo"],),
        )
