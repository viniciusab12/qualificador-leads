"""Componentes visuais reutilizáveis (banner e selo de classificação)."""

import html
import logging
import string

import streamlit as st

# Registro de erros: aparece no terminal (local) e em "Manage app" → logs (Streamlit Cloud)
registro = logging.getLogger("termo")

CLASSES_SELO = {
    "Quente": "selo--quente",
    "Morno": "selo--morno",
    "Frio": "selo--frio",
}


def mostrar_erro(mensagem, erro=None):
    """Mostra uma frase simples para o usuário e guarda o erro técnico no registro.

    O detalhe técnico (nome de tabela, código do servidor, etc.) não aparece na
    tela: ele não ajuda quem está usando e pode revelar como o sistema é feito.
    """
    st.error(mensagem)
    if erro is not None:
        registro.error("%s | %r", mensagem, erro)


def texto_seguro(valor):
    """Prepara um texto digitado pelo usuário para aparecer em st.write ou st.markdown.

    Coloca uma barra antes de cada sinal de pontuação, para que o texto apareça
    exatamente como foi digitado: [texto](link) não vira link, **x** não vira
    negrito e ![](imagem) não carrega imagem de outro site.
    """
    texto = str(valor)
    return "".join("\\" + letra if letra in string.punctuation else letra for letra in texto)


def texto_seguro_com_linhas(valor):
    """Igual a texto_seguro, mas mantém as quebras de linha (para a análise da IA)."""
    return "  \n".join(texto_seguro(linha) for linha in str(valor).splitlines())


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
