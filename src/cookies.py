"""Grava e apaga o cookie de sessão do login com e-mail.

O Streamlit lê cookies sozinho (st.context.cookies), mas não grava.
Para gravar, usamos o CookieManager da biblioteca extra-streamlit-components.
"""

from datetime import datetime, timedelta

import extra_streamlit_components as stx
import streamlit as st

from src.auth import CHAVE_APAGAR_COOKIE, CHAVE_SALVAR_COOKIE, NOME_COOKIE

DIAS_LEMBRAR = 14


def atualizar_cookie():
    """Aplica os pedidos pendentes: salvar o token novo ou apagar o cookie."""
    gerenciador = stx.CookieManager(key="gerenciador_cookies")

    token = st.session_state.get(CHAVE_SALVAR_COOKIE)
    if token:
        # O pedido só sai da fila quando o navegador confirma que o cookie foi gravado
        if gerenciador.get(NOME_COOKIE) == token:
            st.session_state.pop(CHAVE_SALVAR_COOKIE, None)
        else:
            gerenciador.set(
                NOME_COOKIE,
                token,
                expires_at=datetime.now() + timedelta(days=DIAS_LEMBRAR),
                secure=True,  # o navegador só envia o cookie por HTTPS (ou no localhost)
                key="salvar_cookie_sessao",
            )
        return

    if st.session_state.pop(CHAVE_APAGAR_COOKIE, False):
        # Mesmo que o cookie não seja apagado, o token já foi cancelado no Supabase
        try:
            gerenciador.delete(NOME_COOKIE, key="apagar_cookie_sessao")
        except Exception:
            pass
