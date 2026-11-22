"""Aplica o estilo visual (CSS) do app."""

from pathlib import Path

import streamlit as st

CAMINHO_CSS = Path(__file__).resolve().parent.parent / "assets" / "estilo.css"


def aplicar_estilo():
    """Lê o arquivo de estilo e aplica na página."""
    css = CAMINHO_CSS.read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")