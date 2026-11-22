import pandas as pd

from src.metricas import (
    calcular_indicadores,
    contar_por_classificacao,
    contar_por_status,
    conversao_por_classificacao,
    leads_para_tabela,
    leads_por_semana,
    nota_media_por_segmento,
)


def criar_tabela_exemplo():
    """5 leads com valores escolhidos para as contas serem fáceis de conferir."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "segmento": ["Varejo", "Varejo", "Saúde", "Saúde", "Educação"],
            "nota": [90, 75, 50, 30, 20],
            "classificacao": ["Quente", "Quente", "Morno", "Frio", "Frio"],
            "status": ["Ganho", "Perdido", "Ganho", "Perdido", "Novo"],
            "criado_em": pd.to_datetime(
                ["2026-11-02", "2026-11-03", "2026-11-10", "2026-11-11", "2026-11-12"]
            ),
        }
    )


def test_indicadores():
    indicadores = calcular_indicadores(criar_tabela_exemplo())

    assert indicadores["total"] == 5
    assert indicadores["percentual_quentes"] == 40.0  # 2 de 5
    assert indicadores["nota_media"] == 53.0           # (90+75+50+30+20) / 5
    assert indicadores["taxa_conversao"] == 50.0       # 2 ganhos em 4 fechados


def test_indicadores_sem_leads():
    indicadores = calcular_indicadores(pd.DataFrame())

    assert indicadores["total"] == 0
    assert indicadores["taxa_conversao"] is None


def test_contagem_por_classificacao_na_ordem_certa():
    resultado = contar_por_classificacao(criar_tabela_exemplo())

    assert resultado["classificacao"].tolist() == ["Quente", "Morno", "Frio"]
    assert resultado["quantidade"].tolist() == [2, 1, 2]


def test_contagem_por_status_inclui_etapas_vazias():
    resultado = contar_por_status(criar_tabela_exemplo())

    assert resultado["status"].tolist() == [
        "Novo", "Em contato", "Proposta enviada", "Ganho", "Perdido"
    ]
    assert resultado["quantidade"].tolist() == [1, 0, 0, 2, 2]


def test_nota_media_por_segmento():
    resultado = nota_media_por_segmento(criar_tabela_exemplo())

    assert resultado["segmento"].tolist() == ["Varejo", "Saúde", "Educação"]
    assert resultado["nota_media"].tolist() == [82.5, 40.0, 20.0]


def test_conversao_por_classificacao():
    resultado = conversao_por_classificacao(criar_tabela_exemplo())

    assert resultado["classificacao"].tolist() == ["Quente", "Morno", "Frio"]
    assert resultado["taxa_conversao"].tolist() == [50.0, 100.0, 0.0]


def test_leads_por_semana():
    resultado = leads_por_semana(criar_tabela_exemplo())

    assert resultado["quantidade"].tolist() == [2, 3]


def test_leads_para_tabela_sem_leads():
    assert leads_para_tabela([]).empty