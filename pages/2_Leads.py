from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.componentes import mostrar_selo
from src.dados import (
    ErroBanco,
    atualizar_status,
    buscar_lead,
    criar_tabela,
    excluir_lead,
    listar_leads,
    modo_demonstracao,
)
from src.models import STATUS_FUNIL
from src.scoring import formatar_reais

criar_tabela()

st.title("Leads cadastrados")
if modo_demonstracao():
    st.caption("Modo demonstração: dados fictícios. Entre na sua conta para ver os seus leads.")

# Mensagem guardada antes do último recarregamento (ex.: "Status atualizado")
if "mensagem" in st.session_state:
    st.success(st.session_state.pop("mensagem"))

try:
    leads = listar_leads()
except ErroBanco as erro:
    st.error(f"Não foi possível carregar os leads. Detalhe: {erro}")
    st.stop()

if not leads:
    st.info("Nenhum lead cadastrado ainda.")
    st.page_link("pages/1_Cadastrar_Lead.py", label="Cadastrar o primeiro lead", icon=":material/add:")
    st.stop()

# Converte a lista de leads em uma tabela do Pandas
tabela = pd.DataFrame([asdict(lead) for lead in leads])
tabela["classificacao"] = tabela["classificacao"].replace("", "Sem nota")

# ---------- Filtros ----------
with st.sidebar:
    st.header("Filtros")
    busca = st.text_input("Buscar empresa")
    filtro_classe = st.multiselect("Classificação", sorted(tabela["classificacao"].unique()))
    filtro_segmento = st.multiselect("Segmento", sorted(tabela["segmento"].unique()))
    filtro_status = st.multiselect("Status", STATUS_FUNIL)

filtrada = tabela
if busca:
    filtrada = filtrada[filtrada["empresa"].str.contains(busca, case=False, regex=False)]
if filtro_classe:
    filtrada = filtrada[filtrada["classificacao"].isin(filtro_classe)]
if filtro_segmento:
    filtrada = filtrada[filtrada["segmento"].isin(filtro_segmento)]
if filtro_status:
    filtrada = filtrada[filtrada["status"].isin(filtro_status)]

# ---------- Tabela ----------
COLUNAS = {
    "id": "ID",
    "empresa": "Empresa",
    "segmento": "Segmento",
    "necessidade": "Necessidade",
    "orcamento": "Orçamento (R$)",
    "nota": "Nota",
    "classificacao": "Classificação",
    "status": "Status",
    "criado_em": "Cadastrado em",
}

st.caption(f"Mostrando {len(filtrada)} de {len(tabela)} leads")
st.dataframe(
    filtrada[list(COLUNAS)].rename(columns=COLUNAS),
    hide_index=True,
    width="stretch",
    column_config={
        "Nota": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        "Orçamento (R$)": st.column_config.NumberColumn(format="%.2f"),
    },
)

if filtrada.empty:
    st.warning("Nenhum lead encontrado com esses filtros.")
    st.stop()

# ---------- Detalhes do lead escolhido ----------
st.divider()
st.subheader("Detalhes e acompanhamento")

rotulos = {linha.id: f"#{linha.id} · {linha.empresa}" for linha in filtrada.itertuples()}
lead_id = st.selectbox("Escolha um lead", list(rotulos), format_func=rotulos.get)
try:
    lead = buscar_lead(lead_id)
except ErroBanco as erro:
    st.error(f"Não foi possível carregar o lead. Detalhe: {erro}")
    st.stop()

if lead is None:
    st.warning("Lead não encontrado.")
    st.stop()

coluna1, coluna2, coluna3 = st.columns(3)
coluna1.metric("Nota", f"{lead.nota}/100")
with coluna2:
    mostrar_selo(lead.classificacao)
coluna3.metric("Status", lead.status)

st.write(f"**Contato:** {lead.contato} ({'decisor' if lead.contato_decisor else 'não é decisor'})")
st.write(f"**Segmento:** {lead.segmento} · **Necessidade:** {lead.necessidade}")
st.write(f"**Orçamento:** {formatar_reais(lead.orcamento)} · **Prazo:** {lead.prazo}")
st.write(f"**Descrição:** {lead.descricao or 'Não informada'}")

with st.expander("Justificativa da nota", expanded=True):
    st.text(lead.justificativa or "Este lead não tem justificativa registrada.")

with st.expander("Análise da IA"):
    if lead.analise_ia:
        st.info(lead.analise_ia)
    else:
        st.write("Este lead não tem análise da IA.")

# ---------- Atualizar status ----------
st.subheader("Atualizar status no funil")

posicao_atual = STATUS_FUNIL.index(lead.status) if lead.status in STATUS_FUNIL else 0
novo_status = st.selectbox("Novo status", STATUS_FUNIL, index=posicao_atual, key=f"status_{lead.id}")

if st.button("Salvar status"):
    try:
        atualizar_status(lead.id, novo_status)
    except (ErroBanco, ValueError) as erro:
        st.error(f"Não foi possível atualizar o status. Detalhe: {erro}")
    else:
        st.session_state["mensagem"] = f"Status do lead #{lead.id} atualizado para {novo_status}."
        st.rerun()

# ---------- Excluir ----------
with st.expander("Excluir lead"):
    st.write("Esta ação não pode ser desfeita.")
    confirmar = st.checkbox("Confirmo que quero excluir este lead", key=f"confirmar_{lead.id}")

    if st.button("Excluir lead", disabled=not confirmar, type="primary"):
        try:
            excluir_lead(lead.id)
        except ErroBanco as erro:
            st.error(f"Não foi possível excluir o lead. Detalhe: {erro}")
        else:
            st.session_state["mensagem"] = f"Lead #{lead.id} excluído."
            st.rerun()