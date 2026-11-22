import pytest

from src.database import (
    abrir_conexao,
    atualizar_status,
    buscar_lead,
    criar_tabela,
    excluir_lead,
    excluir_todos_leads,
    listar_leads,
    salvar_lead,
)
from src.models import Lead


def criar_lead_exemplo(empresa="Padaria Teste"):
    """Cria um lead fictício para usar nos testes."""
    return Lead(
        empresa=empresa,
        contato="Ana",
        segmento="Varejo",
        necessidade="Site institucional",
        descricao="Site simples com cardápio",
        orcamento=3000,
        prazo="Até 1 mês",
        contato_decisor=True,
    )


def test_salvar_e_buscar_lead(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)

    novo_id = salvar_lead(criar_lead_exemplo(), banco)
    lead = buscar_lead(novo_id, banco)

    assert lead is not None
    assert lead.empresa == "Padaria Teste"
    assert lead.contato_decisor is True
    assert lead.status == "Novo"
    assert lead.criado_em != ""


def test_listar_leads_do_mais_novo_para_o_mais_antigo(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)

    salvar_lead(criar_lead_exemplo("Empresa A"), banco)
    salvar_lead(criar_lead_exemplo("Empresa B"), banco)
    leads = listar_leads(banco)

    assert len(leads) == 2
    assert leads[0].empresa == "Empresa B"
    assert leads[1].empresa == "Empresa A"


def test_buscar_lead_inexistente_retorna_none(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)

    assert buscar_lead(999, banco) is None


def test_atualizar_status(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)
    novo_id = salvar_lead(criar_lead_exemplo(), banco)

    assert atualizar_status(novo_id, "Em contato", banco) is True
    assert buscar_lead(novo_id, banco).status == "Em contato"
    assert atualizar_status(999, "Em contato", banco) is False


def test_status_invalido_gera_erro(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)
    novo_id = salvar_lead(criar_lead_exemplo(), banco)

    with pytest.raises(ValueError):
        atualizar_status(novo_id, "Fechadoo", banco)

    assert buscar_lead(novo_id, banco).status == "Novo"


def test_excluir_lead(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)
    novo_id = salvar_lead(criar_lead_exemplo(), banco)

    assert excluir_lead(novo_id, banco) is True
    assert buscar_lead(novo_id, banco) is None
    assert excluir_lead(novo_id, banco) is False


def test_salvar_lead_com_data_informada(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)

    novo_id = salvar_lead(criar_lead_exemplo(), banco, criado_em="2026-09-15 10:30:00")

    assert buscar_lead(novo_id, banco).criado_em == "2026-09-15 10:30:00"


def test_excluir_todos_leads_reinicia_os_ids(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)
    salvar_lead(criar_lead_exemplo("Empresa A"), banco)
    salvar_lead(criar_lead_exemplo("Empresa B"), banco)

    assert excluir_todos_leads(banco) == 2
    assert listar_leads(banco) == []

    novo_id = salvar_lead(criar_lead_exemplo("Empresa C"), banco)
    assert novo_id == 1


def test_erro_no_meio_desfaz_as_alteracoes(tmp_path):
    banco = tmp_path / "teste.db"
    criar_tabela(banco)

    with pytest.raises(RuntimeError):
        with abrir_conexao(banco) as conexao:
            conexao.execute(
                "INSERT INTO leads (empresa, contato, segmento, necessidade, orcamento, prazo, contato_decisor) "
                "VALUES ('Temporaria', 'X', 'Varejo', 'Site institucional', 0, 'Indefinido', 0)"
            )
            raise RuntimeError("erro simulado no meio da operação")

    assert listar_leads(banco) == []