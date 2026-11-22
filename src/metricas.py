"""Cálculos do dashboard, feitos com Pandas.

Cada função recebe a tabela de leads e devolve um número ou uma tabela pronta
para virar gráfico. Nenhuma função aqui desenha nada na tela.
"""

from dataclasses import asdict

import pandas as pd

from src.models import STATUS_FUNIL

ORDEM_CLASSIFICACAO = ["Quente", "Morno", "Frio"]


def leads_para_tabela(leads):
    """Converte a lista de leads em DataFrame, com a data no formato de data."""
    if not leads:
        return pd.DataFrame()

    tabela = pd.DataFrame([asdict(lead) for lead in leads])
    tabela["criado_em"] = pd.to_datetime(tabela["criado_em"])
    return tabela


def calcular_indicadores(tabela):
    """Devolve os números principais do dashboard."""
    total = len(tabela)
    if total == 0:
        return {"total": 0, "percentual_quentes": 0.0, "nota_media": 0.0, "taxa_conversao": None}

    quentes = (tabela["classificacao"] == "Quente").sum()
    ganhos = (tabela["status"] == "Ganho").sum()
    perdidos = (tabela["status"] == "Perdido").sum()
    fechados = ganhos + perdidos

    return {
        "total": int(total),
        "percentual_quentes": float(round(quentes / total * 100, 1)),
        "nota_media": float(round(tabela["nota"].mean(), 1)),
        "taxa_conversao": float(round(ganhos / fechados * 100, 1)) if fechados else None,
    }


def contar_por_classificacao(tabela):
    """Quantidade de leads em cada classificação, na ordem Quente, Morno, Frio."""
    contagem = tabela["classificacao"].value_counts()
    contagem = contagem.reindex(ORDEM_CLASSIFICACAO, fill_value=0)
    return contagem.rename_axis("classificacao").reset_index(name="quantidade")


def contar_por_segmento(tabela):
    """Quantidade de leads por segmento, do maior para o menor."""
    contagem = tabela["segmento"].value_counts()
    return contagem.rename_axis("segmento").reset_index(name="quantidade")


def contar_por_status(tabela):
    """Quantidade de leads em cada etapa do funil, na ordem do funil."""
    contagem = tabela["status"].value_counts()
    contagem = contagem.reindex(STATUS_FUNIL, fill_value=0)
    return contagem.rename_axis("status").reset_index(name="quantidade")


def nota_media_por_segmento(tabela):
    """Nota média de cada segmento, da maior para a menor."""
    medias = tabela.groupby("segmento", as_index=False)["nota"].mean()
    medias["nota"] = medias["nota"].round(1)
    medias = medias.rename(columns={"nota": "nota_media"})
    return medias.sort_values("nota_media", ascending=False, ignore_index=True)


def conversao_por_classificacao(tabela):
    """Percentual de leads ganhos entre os fechados (Ganho ou Perdido), por classificação."""
    fechados = tabela[tabela["status"].isin(["Ganho", "Perdido"])]
    if fechados.empty:
        return pd.DataFrame(columns=["classificacao", "taxa_conversao"])

    fechados = fechados.assign(ganho=fechados["status"] == "Ganho")
    taxas = fechados.groupby("classificacao", as_index=False)["ganho"].mean()
    taxas["taxa_conversao"] = (taxas["ganho"] * 100).round(1)

    taxas["classificacao"] = pd.Categorical(
        taxas["classificacao"], categories=ORDEM_CLASSIFICACAO, ordered=True
    )
    taxas = taxas.sort_values("classificacao", ignore_index=True)
    taxas["classificacao"] = taxas["classificacao"].astype(str)
    return taxas[["classificacao", "taxa_conversao"]]


def leads_por_semana(tabela):
    """Quantidade de leads cadastrados em cada semana."""
    semanal = tabela.set_index("criado_em").resample("W")["id"].count()
    return semanal.rename_axis("semana").reset_index(name="quantidade")

COLUNAS_CSV = {
    "id": "ID",
    "empresa": "Empresa",
    "contato": "Contato",
    "segmento": "Segmento",
    "necessidade": "Necessidade",
    "descricao": "Descrição",
    "orcamento": "Orçamento (R$)",
    "prazo": "Prazo",
    "contato_decisor": "Contato decisor",
    "nota": "Nota",
    "classificacao": "Classificação",
    "status": "Status",
    "proximo_contato": "Próximo contato",
    "criado_em": "Cadastrado em",
    "justificativa": "Justificativa",
}


def leads_para_csv(leads):
    """Gera o arquivo CSV dos leads, pronto para abrir no Excel em português.

    Usa ponto e vírgula entre as colunas e vírgula nos decimais (padrão do Excel
    no Brasil) e a codificação utf-8-sig, para os acentos aparecerem certos.
    """
    if leads:
        tabela = pd.DataFrame([asdict(lead) for lead in leads])[list(COLUNAS_CSV)]
    else:
        tabela = pd.DataFrame(columns=list(COLUNAS_CSV))
    tabela["contato_decisor"] = tabela["contato_decisor"].map({True: "Sim", False: "Não"})
    tabela = tabela.rename(columns=COLUNAS_CSV)
    return tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
