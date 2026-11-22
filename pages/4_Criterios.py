import pandas as pd
import streamlit as st

from src import criterios
from src.componentes import mostrar_erro
from src.dados import (
    ErroBanco,
    buscar_criterios,
    modo_demonstracao,
    recalcular_todos,
    salvar_criterios,
)
from src.models import Lead
from src.scoring import calcular_pontuacao

# Lead fixo usado na prévia, para comparar as regras novas com as atuais
LEAD_EXEMPLO = Lead(
    empresa="Lead de exemplo",
    contato="Ana",
    segmento="Serviços",
    necessidade="Loja virtual",
    descricao="Loja com catálogo de 80 produtos e pagamento online",
    orcamento=6000,
    prazo="1 a 3 meses",
    contato_decisor=False,
)

st.title("Critérios de pontuação")
st.write(
    "Ajuste o peso de cada critério e os limites de classificação. "
    "A nota continua sendo calculada por regras fixas em Python: a IA não participa."
)

if modo_demonstracao():
    st.info("Modo demonstração: as regras que você salvar valem só nesta sessão.")

if "mensagem_criterios" in st.session_state:
    st.success(st.session_state.pop("mensagem_criterios"))

try:
    atual = buscar_criterios()
except ErroBanco as erro:
    mostrar_erro("Não foi possível carregar as regras agora. Tente de novo em alguns instantes.", erro)
    st.stop()

if atual["versao"]:
    st.caption(f"Regras em uso: versão {atual['versao']} (personalizadas).")
else:
    st.caption("Regras em uso: padrão do Termo.")

# Os campos ficam fora de um formulário para a soma e a prévia mudarem na hora
st.subheader("Pesos")
st.caption("O peso é a pontuação máxima de cada critério. Os 5 pesos precisam somar 100.")

pesos = {}
colunas = st.columns(5)
for coluna, (chave, nome) in zip(colunas, criterios.NOMES_CRITERIOS.items()):
    pesos[chave] = coluna.number_input(
        nome,
        min_value=0,
        max_value=100,
        step=1,
        value=int(atual["pesos"][chave]),
        key=f"peso_{chave}",
    )

soma = sum(pesos.values())
if soma == 100:
    st.success("Soma dos pesos: 100.")
else:
    st.warning(f"Soma dos pesos: {soma}. Ajuste para chegar a 100.")

st.subheader("Classificação")
coluna_quente, coluna_morno = st.columns(2)
limite_quente = coluna_quente.number_input(
    "Quente a partir de", min_value=1, max_value=100, step=1, value=int(atual["limite_quente"])
)
limite_morno = coluna_morno.number_input(
    "Morno a partir de", min_value=1, max_value=100, step=1, value=int(atual["limite_morno"])
)
st.caption(f"Abaixo de {limite_morno} pontos, o lead é Frio.")

st.subheader("Segmentos")
opcoes_segmento = [s for s in criterios.SEGMENTOS_DISPONIVEIS if s != "Outro"]
segmentos_alvo = st.multiselect(
    "Segmentos-alvo (pontuação máxima do critério)",
    opcoes_segmento,
    default=[s for s in atual["segmentos_alvo"] if s in opcoes_segmento],
)
segmentos_secundarios = st.multiselect(
    "Segmentos secundários (metade da pontuação)",
    [s for s in opcoes_segmento if s not in segmentos_alvo],
    default=[
        s for s in atual["segmentos_secundarios"] if s in opcoes_segmento and s not in segmentos_alvo
    ],
)

st.subheader("Descrição")
tamanho_minimo = st.number_input(
    "Tamanho mínimo da descrição para ganhar os pontos de detalhamento (caracteres)",
    min_value=0,
    max_value=500,
    step=5,
    value=int(atual["tamanho_minimo_descricao"]),
)

proposta = {
    "pesos": {chave: int(valor) for chave, valor in pesos.items()},
    "limite_quente": int(limite_quente),
    "limite_morno": int(limite_morno),
    "segmentos_alvo": segmentos_alvo,
    "segmentos_secundarios": segmentos_secundarios,
    "tamanho_minimo_descricao": int(tamanho_minimo),
}
erros = criterios.validar_criterios(proposta)

# ---------- Prévia ----------
st.subheader("Prévia")
st.caption("O mesmo lead de exemplo pontuado com as regras em uso e com as regras desta página.")

resultado_atual = calcular_pontuacao(LEAD_EXEMPLO, atual)
coluna_antes, coluna_depois = st.columns(2)
coluna_antes.metric("Regras em uso", f"{resultado_atual['nota']}/100", resultado_atual["classificacao"], delta_color="off")
if erros:
    coluna_depois.metric("Regras desta página", "—")
else:
    resultado_novo = calcular_pontuacao(LEAD_EXEMPLO, criterios.completar_criterios(proposta))
    coluna_depois.metric(
        "Regras desta página",
        f"{resultado_novo['nota']}/100",
        resultado_novo["classificacao"],
        delta_color="off",
    )
    with st.expander("Justificativa com as regras desta página"):
        st.text(resultado_novo["justificativa"])

tabela_lead = pd.DataFrame(
    {
        "Campo": ["Segmento", "Necessidade", "Orçamento", "Prazo", "Contato decisor"],
        "Valor": ["Serviços", "Loja virtual", "R$ 6.000", "1 a 3 meses", "Não"],
    }
)
with st.expander("Dados do lead de exemplo"):
    st.dataframe(tabela_lead, hide_index=True)

# ---------- Salvar ----------
st.divider()
for erro in erros:
    st.error(erro)

coluna_salvar, coluna_padrao = st.columns(2)
if coluna_salvar.button("Salvar regras", type="primary", disabled=bool(erros), width="stretch"):
    try:
        versao = salvar_criterios(proposta)
    except ValueError as erro:
        st.error(str(erro))
    except ErroBanco as erro:
        mostrar_erro("Não foi possível salvar as regras agora. Tente de novo.", erro)
    else:
        st.session_state["mensagem_criterios"] = (
            f"Regras salvas (versão {versao}). Os leads novos já usam essas regras. "
            "Para aplicar nos leads antigos, use Recalcular todos os leads."
        )
        st.rerun()

if coluna_padrao.button("Voltar às regras padrão", width="stretch", disabled=atual["versao"] == 0):
    try:
        versao = salvar_criterios(criterios.criterios_padrao())
    except ErroBanco as erro:
        mostrar_erro("Não foi possível salvar as regras agora. Tente de novo.", erro)
    else:
        for chave in criterios.NOMES_CRITERIOS:
            st.session_state.pop(f"peso_{chave}", None)
        st.session_state["mensagem_criterios"] = f"Regras padrão restauradas (versão {versao})."
        st.rerun()

# ---------- Recalcular ----------
st.subheader("Recalcular leads antigos")
st.caption(
    "Mudar as regras não altera as notas já calculadas. Recalcular aplica as regras em uso "
    "em todos os leads e registra a versão em cada um. A análise da IA não muda."
)
confirmar = st.checkbox("Quero recalcular a nota de todos os meus leads")
if st.button("Recalcular todos os leads", disabled=not confirmar):
    try:
        with st.spinner("Recalculando..."):
            alterados = recalcular_todos()
    except ErroBanco as erro:
        mostrar_erro("Não foi possível recalcular agora. Tente de novo.", erro)
    else:
        st.session_state["mensagem_criterios"] = f"Leads recalculados. {alterados} mudaram de nota ou classificação."
        st.rerun()
