from src.database import (
    atualizar_status,
    buscar_lead,
    criar_tabela,
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