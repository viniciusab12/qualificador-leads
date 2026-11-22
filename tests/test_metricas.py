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

def test_csv_abre_no_excel_em_portugues():
    from src.metricas import leads_para_csv

    from src.models import Lead

    lead = Lead(
        empresa="Padaria Vida",
        contato="Ana",
        segmento="Alimentação",
        necessidade="Site institucional",
        descricao="Site com cardápio",
        orcamento=2500.5,
        prazo="Até 1 mês",
        contato_decisor=True,
        nota=80,
        classificacao="Quente",
        id=1,
    )
    conteudo = leads_para_csv([lead]).decode("utf-8-sig")
    cabecalho, primeira_linha = conteudo.splitlines()[:2]

    assert cabecalho.startswith("ID;Empresa;Contato;Segmento")
    assert "Próximo contato" in cabecalho
    assert ";Sim;" in primeira_linha
    assert "2500,5" in primeira_linha  # vírgula nos decimais


def test_csv_sem_leads_tem_so_o_cabecalho():
    from src.metricas import leads_para_csv

    conteudo = leads_para_csv([]).decode("utf-8-sig")

    assert conteudo.strip().startswith("ID;Empresa")
    assert len(conteudo.strip().splitlines()) == 1



# ---------- Proteção contra fórmulas no CSV (CSV Injection) ----------

import csv  # noqa: E402
import io  # noqa: E402

import pytest  # noqa: E402

from src.metricas import leads_para_csv, proteger_celula  # noqa: E402
from src.models import Lead  # noqa: E402


@pytest.mark.parametrize(
    "valor",
    [
        '=HYPERLINK("http://site-falso.com";"Clique")',
        "+5511999999999",
        "-2+3",
        "@SOMA(A1:A2)",
        "\t=1+1",
        "  =1+1",
    ],
)
def test_texto_que_viraria_formula_ganha_apostrofo(valor):
    assert proteger_celula(valor) == "'" + valor


def test_texto_comum_e_numeros_nao_mudam():
    assert proteger_celula("Padaria Vida") == "Padaria Vida"
    assert proteger_celula("Email: ana@empresa.com") == "Email: ana@empresa.com"
    assert proteger_celula("") == ""
    assert proteger_celula(2500.5) == 2500.5
    assert proteger_celula(None) is None


def test_csv_exportado_nao_tem_formula():
    lead = Lead(
        empresa="=HYPERLINK(\"http://site-falso.com\";\"Clique\")",
        contato="@Ana",
        segmento="Varejo",
        necessidade="Loja virtual",
        descricao="-desconto de 10%",
        orcamento=8000.0,
        prazo="Até 1 mês",
        contato_decisor=True,
        nota=80,
        classificacao="Quente",
        id=7,
    )

    texto = leads_para_csv([lead]).decode("utf-8-sig")
    celulas = list(csv.reader(io.StringIO(texto), delimiter=";"))[1]

    assert celulas[0] == "7"                    # ID continua número
    assert celulas[1].startswith("'=HYPERLINK")
    assert celulas[2] == "'@Ana"
    assert celulas[5] == "'-desconto de 10%"
    assert celulas[6] == "8000,0"               # orçamento continua número
