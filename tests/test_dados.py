import pytest

from src import dados
from src.models import Lead


def lead_exemplo(id_lead, empresa):
    return Lead(
        empresa=empresa,
        contato="Contato",
        segmento="Varejo",
        necessidade="Loja virtual",
        descricao="",
        orcamento=5000.0,
        prazo="Até 1 mês",
        contato_decisor=True,
        id=id_lead,
    )


def sessao_de_visitante(monkeypatch, sessao=None):
    """Visitante sem login, com 2 leads de exemplo na base compartilhada.

    A base compartilhada é só lida: se o código tentar gravar nela, o teste falha.
    Devolve o dicionário que faz o papel da sessão do visitante.
    """
    sessao = {} if sessao is None else sessao
    exemplos = [lead_exemplo(2, "Exemplo 2"), lead_exemplo(1, "Exemplo 1")]

    def proibido(*args, **kwargs):
        raise AssertionError("O modo demonstração não pode alterar a base compartilhada")

    monkeypatch.setattr(dados, "usuario_atual", lambda: None)
    monkeypatch.setattr(dados, "_sessao", lambda: sessao)
    monkeypatch.setattr(dados.demo, "listar_leads", lambda: list(exemplos))
    monkeypatch.setattr(dados.demo, "salvar_lead", proibido)
    monkeypatch.setattr(dados.demo, "atualizar_status", proibido)
    monkeypatch.setattr(dados.demo, "excluir_lead", proibido)
    return sessao


def test_sem_login_usa_base_de_demonstracao(monkeypatch):
    sessao_de_visitante(monkeypatch)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", lambda email: ["lead do usuário"])

    assert [lead.empresa for lead in dados.listar_leads()] == ["Exemplo 2", "Exemplo 1"]
    assert dados.modo_demonstracao() is True


def test_com_login_usa_os_leads_do_usuario(monkeypatch):
    usuario = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", lambda email: [f"leads de {email}"])

    assert dados.listar_leads() == ["leads de ana@empresa.com"]
    assert dados.modo_demonstracao() is False


def test_falha_no_banco_vira_erro_banco(monkeypatch):
    def falhar(email):
        raise ConnectionError("sem internet")

    usuario = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", falhar)

    with pytest.raises(dados.ErroBanco):
        dados.listar_leads()


def test_status_invalido_continua_como_value_error(monkeypatch):
    sessao_de_visitante(monkeypatch)

    with pytest.raises(ValueError):
        dados.atualizar_status(1, "Fechadoo")


def test_github_usa_o_identificador_da_conta_como_dono(monkeypatch):
    usuario = {"dono": "github|12345", "email": "", "nome": "ana-dev", "provedor": "github"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", lambda dono: [f"leads de {dono}"])

    assert dados.listar_leads() == ["leads de github|12345"]


# ---------- Modo demonstração: cada visitante tem a própria sessão ----------

def test_lead_novo_fica_so_na_sessao_do_visitante(monkeypatch):
    sessao = sessao_de_visitante(monkeypatch)

    novo_id = dados.salvar_lead(lead_exemplo(None, "Lead do visitante"))

    assert novo_id == 3
    assert dados.buscar_lead(novo_id).empresa == "Lead do visitante"
    assert dados.listar_leads()[0].empresa == "Lead do visitante"
    assert len(sessao[dados.CHAVE_NOVOS]) == 1


def test_status_alterado_fica_so_na_sessao(monkeypatch):
    sessao_de_visitante(monkeypatch)

    assert dados.atualizar_status(1, "Ganho") is True
    assert dados.buscar_lead(1).status == "Ganho"


def test_exclusao_esconde_o_lead_so_para_o_visitante(monkeypatch):
    sessao_de_visitante(monkeypatch)

    assert dados.excluir_lead(1) is True
    assert dados.buscar_lead(1) is None
    assert [lead.empresa for lead in dados.listar_leads()] == ["Exemplo 2"]


def test_excluir_lead_novo_do_visitante(monkeypatch):
    sessao_de_visitante(monkeypatch)
    novo_id = dados.salvar_lead(lead_exemplo(None, "Lead do visitante"))

    assert dados.excluir_lead(novo_id) is True
    assert dados.buscar_lead(novo_id) is None


def test_lead_inexistente_na_demonstracao(monkeypatch):
    sessao_de_visitante(monkeypatch)

    assert dados.atualizar_status(99, "Ganho") is False
    assert dados.excluir_lead(99) is False


def test_dois_visitantes_nao_veem_as_mudancas_um_do_outro(monkeypatch):
    sessao_ana, sessao_bruno = {}, {}

    sessao_de_visitante(monkeypatch, sessao_ana)
    dados.excluir_lead(1)
    dados.salvar_lead(lead_exemplo(None, "Lead da Ana"))

    sessao_de_visitante(monkeypatch, sessao_bruno)
    assert [lead.empresa for lead in dados.listar_leads()] == ["Exemplo 2", "Exemplo 1"]


def test_limite_de_analises_com_ia_na_demonstracao(monkeypatch):
    sessao_de_visitante(monkeypatch)

    for _ in range(dados.LIMITE_IA_DEMO):
        assert dados.pode_usar_ia() is True
        dados.registrar_uso_ia()

    assert dados.pode_usar_ia() is False


def test_usuario_logado_nao_tem_limite_de_ia(monkeypatch):
    usuario = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados, "_sessao", lambda: {dados.CHAVE_USO_IA: 100})

    assert dados.pode_usar_ia() is True
