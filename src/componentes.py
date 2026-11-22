"""Componentes visuais reutilizáveis (banner e selo de classificação)."""

import html

import streamlit as st

CLASSES_SELO = {
    "Quente": "selo--quente",
    "Morno": "selo--morno",
    "Frio": "selo--frio",
}


def banner(titulo, texto, rotulo=""):
    """Mostra o banner em degradê no topo da página."""
    conteudo = (
        '<div class="termo-banner">'
        f'<div class="termo-banner__rotulo">{html.escape(rotulo)}</div>'
        f'<div class="termo-banner__titulo">{html.escape(titulo)}</div>'
        f'<p class="termo-banner__texto">{html.escape(texto)}</p>'
        "</div>"
    )
    st.markdown(conteudo, unsafe_allow_html=True)


def selo(classificacao):
    """Devolve o HTML do selo colorido de uma classificação."""
    classe = CLASSES_SELO.get(classificacao, "selo--sem-nota")
    texto = classificacao or "Sem nota"
    return f'<span class="selo {classe}">{html.escape(texto)}</span>'


def mostrar_selo(classificacao, legenda="Classificação"):
    """Mostra uma legenda pequena e o selo logo abaixo."""
    st.caption(legenda)
    st.markdown(selo(classificacao), unsafe_allow_html=True)
