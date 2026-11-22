from src.supabase_db import formatar_data, linha_para_lead


def test_formatar_data_converte_para_horario_de_brasilia():
    # 12:00 em UTC = 09:00 em Brasília
    assert formatar_data("2026-11-22T12:00:00+00:00") == "2026-11-22 09:00:00"


def test_formatar_data_vazia():
    assert formatar_data(None) == ""


def test_linha_para_lead_converte_tipos_e_ignora_dono():
    linha = {
        "id": 7,
        "dono_email": "ana@empresa.com",
        "empresa": "Empresa Teste",
        "contato": "Ana",
        "segmento": "Varejo",
        "necessidade": "Loja virtual",
        "descricao": None,
        "orcamento": "2500.00",
        "prazo": "Até 1 mês",
        "contato_decisor": True,
        "nota": 75,
        "classificacao": "Quente",
        "justificativa": "Orçamento: 15/30",
        "analise_ia": None,
        "status": "Novo",
        "criado_em": "2026-11-22T12:00:00+00:00",
    }

    lead = linha_para_lead(linha)

    assert lead.id == 7
    assert lead.orcamento == 2500.0
    assert lead.descricao == ""
    assert lead.analise_ia == ""
    assert lead.criado_em == "2026-11-22 09:00:00"
