from dataclasses import asdict, replace
from datetime import date

import pandas as pd
import streamlit as st

from src import criterios
from src.ai_analyzer import analisar_lead
from src.componentes import mostrar_erro, mostrar_selo, texto_seguro, texto_seguro_com_linhas
from src.dados import (
    ErroBanco,
    adicionar_anotacao,
    atualizar_campos,
    atualizar_status,
    buscar_lead,
    campos_da_pontuacao,
    definir_proximo_contato,
    excluir_lead,
    listar_leads,
    modo_demonstracao,
    pode_usar_ia,
    pontuar,
    registrar_uso_ia,
)
from src.metricas import leads_para_csv
from src.models import STATUS_FUNIL
from src.scoring import formatar_reais

NECESSIDADES = criterios.SERVICOS_OFERECIDOS + ["Outro"]
PRAZOS = list(criterios.PONTOS_PRAZO.keys())


def opcoes_com(valor, opcoes):
    """Garante que o valor atual do lead apareça na lista, mesmo que não esteja nas opções."""
    return opcoes if valor in opcoes else [valor] + opcoes


def formatar_data_br(texto_iso):
    """'2026-11-22' -> '22/11/2026'."""
    return date.fromisoformat(texto_iso[:10]).strftime("%d/%m/%Y")


st.title("Leads cadastrados")
if modo_demonstracao():
    st.caption(
        "Modo demonstração: dados fictícios. O que você cadastrar, alterar ou excluir "
        "fica só nesta sessão. Entre na sua conta para ver os seus leads."
    )

# Mensagem guardada antes do último recarregamento (ex.: "Status atualizado")
if "mensagem" in st.session_state:
    st.success(st.session_state.pop("mensagem"))

try:
    leads = listar_leads()
except ErroBanco as erro:
    mostrar_erro("Não foi possível carregar os leads agora. Tente de novo em alguns instantes. Se continuar, recarregue a página.", erro)
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
    "proximo_contato": "Próximo contato",
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

ids_filtrados = set(filtrada["id"])
st.download_button(
    "Baixar estes leads em CSV",
    data=leads_para_csv([lead for lead in leads if lead.id in ids_filtrados]),
    file_name=f"leads_termo_{date.today().isoformat()}.csv",
    mime="text/csv",
    icon=":material/download:",
    help="Abre no Excel. Usa os filtros da barra lateral.",
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
    mostrar_erro("Não foi possível abrir este lead agora. Tente de novo em alguns instantes. Se continuar, recarregue a página.", erro)
    st.stop()

if lead is None:
    st.warning("Lead não encontrado.")
    st.stop()

coluna1, coluna2, coluna3 = st.columns(3)
coluna1.metric("Nota", f"{lead.nota}/100")
with coluna2:
    mostrar_selo(lead.classificacao)
coluna3.metric("Status", lead.status)

# Textos digitados passam por texto_seguro: aparecem como foram escritos, sem virar link ou imagem
decisor = "decisor" if lead.contato_decisor else "não é decisor"
st.write(f"**Contato:** {texto_seguro(lead.contato)} ({decisor})")
st.write(f"**Segmento:** {lead.segmento} · **Necessidade:** {lead.necessidade}")
st.write(f"**Orçamento:** {formatar_reais(lead.orcamento)} · **Prazo:** {lead.prazo}")
st.write(f"**Descrição:** {texto_seguro(lead.descricao) if lead.descricao else 'Não informada'}")

with st.expander("Justificativa da nota", expanded=True):
    st.text(lead.justificativa or "Este lead não tem justificativa registrada.")

with st.expander("Análise da IA"):
    if lead.analise_ia:
        st.info(texto_seguro_com_linhas(lead.analise_ia))
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
        mostrar_erro("Não foi possível atualizar o status agora. Tente de novo.", erro)
    else:
        st.session_state["mensagem"] = f"Status do lead #{lead.id} atualizado para {novo_status}."
        st.rerun()

# ---------- Próximo contato ----------
st.subheader("Próximo contato")

data_atual = date.fromisoformat(lead.proximo_contato) if lead.proximo_contato else None
nova_data = st.date_input(
    "Data do próximo contato",
    value=data_atual,
    format="DD/MM/YYYY",
    key=f"proximo_{lead.id}",
    help="Os leads com contato marcado para hoje aparecem na página Início.",
)
coluna_salvar, coluna_limpar = st.columns(2)
if coluna_salvar.button("Salvar data", key=f"salvar_data_{lead.id}", width="stretch"):
    try:
        definir_proximo_contato(lead.id, nova_data)
    except (ErroBanco, ValueError) as erro:
        mostrar_erro("Não foi possível salvar a data agora. Tente de novo.", erro)
    else:
        st.session_state["mensagem"] = f"Próximo contato do lead #{lead.id} atualizado."
        st.rerun()
if coluna_limpar.button("Limpar data", key=f"limpar_data_{lead.id}", width="stretch", disabled=data_atual is None):
    try:
        definir_proximo_contato(lead.id, None)
    except (ErroBanco, ValueError) as erro:
        mostrar_erro("Não foi possível limpar a data agora. Tente de novo.", erro)
    else:
        st.session_state["mensagem"] = f"Próximo contato do lead #{lead.id} removido."
        st.rerun()

# ---------- Anotações ----------
st.subheader("Anotações")

if lead.anotacoes:
    for anotacao in reversed(lead.anotacoes):
        quando = formatar_data_br(anotacao["data"]) + anotacao["data"][10:]
        st.markdown(f"**{quando}** · {texto_seguro(anotacao['texto'])}")
else:
    st.caption("Nenhuma anotação ainda. Registre ligações, reuniões e combinados.")

with st.form(f"form_anotacao_{lead.id}", clear_on_submit=True):
    texto_anotacao = st.text_area("Nova anotação", max_chars=500, height=80)
    if st.form_submit_button("Adicionar anotação"):
        try:
            adicionar_anotacao(lead.id, texto_anotacao)
        except ValueError as erro:
            st.warning(str(erro))
        except ErroBanco as erro:
            mostrar_erro("Não foi possível salvar a anotação agora. Tente de novo.", erro)
        else:
            st.session_state["mensagem"] = f"Anotação adicionada ao lead #{lead.id}."
            st.rerun()

# ---------- Editar dados ----------
with st.expander("Editar dados do lead"):
    st.caption("Ao salvar, a nota é recalculada com as regras atuais da página Critérios.")
    with st.form(f"form_editar_{lead.id}"):
        coluna_a, coluna_b = st.columns(2)
        with coluna_a:
            empresa = st.text_input("Empresa *", value=lead.empresa, max_chars=100)
            segmento = st.selectbox(
                "Segmento *",
                opcoes_com(lead.segmento, criterios.SEGMENTOS_DISPONIVEIS),
                index=opcoes_com(lead.segmento, criterios.SEGMENTOS_DISPONIVEIS).index(lead.segmento),
            )
            orcamento = st.number_input(
                "Orçamento (R$) *", min_value=0.0, step=500.0, format="%.2f", value=float(lead.orcamento)
            )
        with coluna_b:
            contato = st.text_input("Nome do contato *", value=lead.contato, max_chars=100)
            necessidade = st.selectbox(
                "Necessidade *",
                opcoes_com(lead.necessidade, NECESSIDADES),
                index=opcoes_com(lead.necessidade, NECESSIDADES).index(lead.necessidade),
            )
            prazo = st.selectbox(
                "Prazo para começar *",
                opcoes_com(lead.prazo, PRAZOS),
                index=opcoes_com(lead.prazo, PRAZOS).index(lead.prazo),
            )
        descricao = st.text_area("Descrição da necessidade", value=lead.descricao, max_chars=1000)
        contato_decisor = st.checkbox("O contato é quem decide a compra", value=lead.contato_decisor)
        nova_analise = st.checkbox(
            "Gerar uma nova análise da IA com os dados atualizados",
            help="Sem marcar, a análise anterior é mantida.",
        )
        salvar_edicao = st.form_submit_button("Salvar alterações", type="primary")

    if salvar_edicao:
        if not empresa.strip() or not contato.strip():
            st.error("Empresa e nome do contato são obrigatórios.")
        else:
            editado = replace(
                lead,
                empresa=empresa.strip(),
                contato=contato.strip(),
                segmento=segmento,
                necessidade=necessidade,
                descricao=descricao.strip(),
                orcamento=orcamento,
                prazo=prazo,
                contato_decisor=contato_decisor,
            )
            pontuar(editado)
            campos = {
                "empresa": editado.empresa,
                "contato": editado.contato,
                "segmento": editado.segmento,
                "necessidade": editado.necessidade,
                "descricao": editado.descricao,
                "orcamento": float(editado.orcamento),
                "prazo": editado.prazo,
                "contato_decisor": editado.contato_decisor,
                **campos_da_pontuacao(editado),
            }
            aviso_ia = None
            if nova_analise:
                permitir_ia = pode_usar_ia()
                with st.spinner("Gerando a análise da IA..."):
                    analise, aviso_ia = analisar_lead(editado, permitir_ia=permitir_ia)
                if permitir_ia:
                    registrar_uso_ia()
                if analise:
                    campos["analise_ia"] = analise
            try:
                atualizar_campos(lead.id, campos)
            except (ErroBanco, ValueError) as erro:
                mostrar_erro("Não foi possível salvar as alterações agora. Tente de novo.", erro)
            else:
                mensagem = f"Lead #{lead.id} atualizado. Nota: {editado.nota}/100 ({editado.classificacao})."
                if aviso_ia:
                    mensagem += f" Aviso da IA: {aviso_ia}"
                st.session_state["mensagem"] = mensagem
                st.rerun()

# ---------- Excluir ----------
with st.expander("Excluir lead"):
    st.write("Esta ação não pode ser desfeita.")
    confirmar = st.checkbox("Confirmo que quero excluir este lead", key=f"confirmar_{lead.id}")

    if st.button("Excluir lead", disabled=not confirmar, type="primary"):
        try:
            excluir_lead(lead.id)
        except ErroBanco as erro:
            mostrar_erro("Não foi possível excluir o lead agora. Tente de novo.", erro)
        else:
            st.session_state["mensagem"] = f"Lead #{lead.id} excluído."
            st.rerun()