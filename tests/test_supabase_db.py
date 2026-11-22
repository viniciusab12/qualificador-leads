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


# ---------- Isolamento entre contas ----------
#
# O app usa a chave service_role, que ignora o RLS do Supabase. Então quem
# separa as contas é o filtro por dono_email em cada função de src/supabase_db.py.
# Estes testes trocam o Supabase por um banco falso, em memória, que:
#   1. aplica os filtros de verdade (para conferir o resultado), e
#   2. anota cada consulta feita (para conferir que o filtro do dono estava lá).

import pytest

from src import supabase_db
from src.models import Lead

ANA = "ana@empresa.com"
BRUNO = "github|98765"


class ConsultaFalsa:
    """Imita o encadeamento do cliente do Supabase: .table().select().eq()...execute()."""

    def __init__(self, banco):
        self.banco = banco
        self.operacao = None
        self.dados = None
        self.filtros = []
        self.limite = None

    def insert(self, dados):
        self.operacao, self.dados = "insert", dados
        return self

    def select(self, colunas="*"):
        self.operacao = "select"
        return self

    def update(self, dados):
        self.operacao, self.dados = "update", dados
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def order(self, coluna, desc=False):
        return self

    def limit(self, quantidade):
        self.limite = quantidade
        return self

    def _combina(self, linha):
        return all(linha.get(coluna) == valor for coluna, valor in self.filtros)

    def execute(self):
        self.banco.consultas.append((self.operacao, list(self.filtros), self.dados))

        if self.operacao == "insert":
            self.banco.ultimo_id += 1
            linha = {**self.dados, "id": self.banco.ultimo_id, "criado_em": "2026-11-22T12:00:00+00:00"}
            self.banco.linhas.append(linha)
            return RespostaFalsa([linha])

        encontradas = [linha for linha in self.banco.linhas if self._combina(linha)]

        if self.operacao == "select":
            encontradas.sort(key=lambda linha: linha["id"], reverse=True)
            if self.limite:
                encontradas = encontradas[: self.limite]
            return RespostaFalsa([dict(linha) for linha in encontradas])

        if self.operacao == "update":
            for linha in encontradas:
                linha.update(self.dados)
            return RespostaFalsa(encontradas)

        if self.operacao == "delete":
            self.banco.linhas = [linha for linha in self.banco.linhas if linha not in encontradas]
            return RespostaFalsa(encontradas)

        raise AssertionError(f"Operação não prevista: {self.operacao}")


class RespostaFalsa:
    def __init__(self, data):
        self.data = data


class BancoFalso:
    def __init__(self):
        self.linhas = []
        self.consultas = []
        self.ultimo_id = 0

    def table(self, nome):
        assert nome == "leads"
        return ConsultaFalsa(self)


def lead_exemplo(empresa):
    return Lead(
        empresa=empresa,
        contato="Contato",
        segmento="Varejo",
        necessidade="Loja virtual",
        descricao="Loja com catálogo e pagamento online",
        orcamento=8000.0,
        prazo="Até 1 mês",
        contato_decisor=True,
        nota=80,
        classificacao="Quente",
        justificativa="Orçamento: 25/30",
    )


@pytest.fixture
def banco(monkeypatch):
    """Banco falso com um lead da Ana e um do Bruno."""
    falso = BancoFalso()
    monkeypatch.setattr(supabase_db, "cliente_banco", lambda: falso)
    supabase_db.salvar_lead(lead_exemplo("Loja da Ana"), ANA)
    supabase_db.salvar_lead(lead_exemplo("Padaria do Bruno"), BRUNO)
    falso.consultas.clear()
    return falso


def id_do_lead(banco, dono):
    return next(linha["id"] for linha in banco.linhas if linha["dono_email"] == dono)


def test_salvar_grava_o_dono_informado_pelo_servidor(banco):
    novo_id = supabase_db.salvar_lead(lead_exemplo("Outra loja"), ANA)

    linha = next(linha for linha in banco.linhas if linha["id"] == novo_id)
    assert linha["dono_email"] == ANA


def test_listar_mostra_so_os_leads_da_conta(banco):
    leads_ana = supabase_db.listar_leads(ANA)
    leads_bruno = supabase_db.listar_leads(BRUNO)

    assert [lead.empresa for lead in leads_ana] == ["Loja da Ana"]
    assert [lead.empresa for lead in leads_bruno] == ["Padaria do Bruno"]


def test_nao_le_lead_de_outra_conta(banco):
    id_bruno = id_do_lead(banco, BRUNO)

    assert supabase_db.buscar_lead(id_bruno, ANA) is None
    assert supabase_db.buscar_lead(id_bruno, BRUNO).empresa == "Padaria do Bruno"


def test_nao_altera_lead_de_outra_conta(banco):
    id_bruno = id_do_lead(banco, BRUNO)

    assert supabase_db.atualizar_status(id_bruno, "Ganho", ANA) is False
    assert supabase_db.buscar_lead(id_bruno, BRUNO).status == "Novo"


def test_nao_exclui_lead_de_outra_conta(banco):
    id_bruno = id_do_lead(banco, BRUNO)

    assert supabase_db.excluir_lead(id_bruno, ANA) is False
    assert supabase_db.buscar_lead(id_bruno, BRUNO) is not None


def test_dono_altera_e_exclui_o_proprio_lead(banco):
    id_ana = id_do_lead(banco, ANA)

    assert supabase_db.atualizar_status(id_ana, "Em contato", ANA) is True
    assert supabase_db.buscar_lead(id_ana, ANA).status == "Em contato"
    assert supabase_db.excluir_lead(id_ana, ANA) is True
    assert supabase_db.buscar_lead(id_ana, ANA) is None


def test_toda_consulta_filtra_pelo_dono(banco):
    """Se uma função nova ou alterada esquecer o filtro do dono, este teste falha."""
    id_ana = id_do_lead(banco, ANA)

    supabase_db.listar_leads(ANA)
    supabase_db.buscar_lead(id_ana, ANA)
    supabase_db.atualizar_status(id_ana, "Em contato", ANA)
    supabase_db.excluir_lead(id_ana, ANA)

    assert len(banco.consultas) == 4
    for operacao, filtros, _ in banco.consultas:
        assert ("dono_email", ANA) in filtros, f"{operacao} rodou sem o filtro do dono"


def test_status_invalido_nao_chega_ao_banco(banco):
    with pytest.raises(ValueError):
        supabase_db.atualizar_status(1, "Fechadoo", ANA)

    assert banco.consultas == []
