import threading

import pytest

from src import dados
from src.models import Lead


@pytest.fixture(autouse=True)
def contador_novo(monkeypatch):
    """Cada teste começa com o contador de análises do servidor zerado.

    O mesmo contador é usado por todas as "sessões" de um teste, como no
    servidor de verdade.
    """
    contador = {"trava": threading.Lock(), "dia": None, "usos": {}}
    monkeypatch.setattr(dados, "_contador_do_servidor", lambda: contador)
    return contador


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


def test_limite_da_sessao_nao_vale_para_usuario_logado(monkeypatch):
    usuario = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados, "_sessao", lambda: {dados.CHAVE_USO_IA: 100})

    assert dados.pode_usar_ia() is True


# ---------- Regras, edição e acompanhamento (modo demonstração) ----------

from datetime import date, datetime  # noqa: E402

from src import criterios  # noqa: E402


def test_regras_padrao_quando_ninguem_personalizou(monkeypatch):
    sessao_de_visitante(monkeypatch)

    assert dados.buscar_criterios() == criterios.criterios_padrao()


def test_salvar_regras_cria_versoes_na_sessao(monkeypatch):
    sessao_de_visitante(monkeypatch)
    config = criterios.criterios_padrao()
    config["limite_quente"] = 80

    assert dados.salvar_criterios(config) == 1
    assert dados.salvar_criterios(config) == 2
    assert dados.buscar_criterios()["limite_quente"] == 80
    assert dados.buscar_criterios()["versao"] == 2


def test_regras_invalidas_nao_sao_salvas(monkeypatch):
    sessao = sessao_de_visitante(monkeypatch)
    config = criterios.criterios_padrao()
    config["pesos"]["orcamento"] = 90

    with pytest.raises(ValueError, match="somar 100"):
        dados.salvar_criterios(config)

    assert dados.CHAVE_CRITERIOS not in sessao


def test_pontuar_usa_as_regras_da_conta(monkeypatch):
    sessao_de_visitante(monkeypatch)
    config = criterios.criterios_padrao()
    config["limite_quente"] = 99
    dados.salvar_criterios(config)
    lead = lead_exemplo(None, "Teste")  # 25 + 25 + 20 + 10 + 10 = 90 pontos

    dados.pontuar(lead)

    assert lead.nota == 90
    assert lead.classificacao == "Morno"
    assert lead.criterios_versao == 1


def test_recalcular_aplica_as_regras_novas(monkeypatch):
    sessao_de_visitante(monkeypatch)
    config = criterios.criterios_padrao()
    config["limite_quente"] = 99
    dados.salvar_criterios(config)

    alterados = dados.recalcular_todos()

    assert alterados == 2
    assert all(lead.classificacao == "Morno" for lead in dados.listar_leads())


def test_editar_campos_na_demonstracao(monkeypatch):
    sessao_de_visitante(monkeypatch)

    assert dados.atualizar_campos(1, {"empresa": "Nome corrigido", "orcamento": 9000.0}) is True

    lead = dados.buscar_lead(1)
    assert lead.empresa == "Nome corrigido"
    assert lead.orcamento == 9000.0


def test_campo_proibido_e_recusado_tambem_na_demonstracao(monkeypatch):
    sessao_de_visitante(monkeypatch)

    with pytest.raises(ValueError):
        dados.atualizar_campos(1, {"id": 99})


def test_anotacoes_ficam_em_ordem_com_data(monkeypatch):
    sessao_de_visitante(monkeypatch)

    dados.adicionar_anotacao(1, "Primeira ligação", agora=datetime(2026, 11, 20, 9, 30))
    dados.adicionar_anotacao(1, "  Enviou o briefing  ", agora=datetime(2026, 11, 21, 15, 0))

    assert dados.buscar_lead(1).anotacoes == [
        {"data": "2026-11-20 09:30", "texto": "Primeira ligação"},
        {"data": "2026-11-21 15:00", "texto": "Enviou o briefing"},
    ]


def test_anotacao_vazia_e_recusada(monkeypatch):
    sessao_de_visitante(monkeypatch)

    with pytest.raises(ValueError):
        dados.adicionar_anotacao(1, "   ")


def test_proximo_contato_e_lista_do_dia(monkeypatch):
    sessao_de_visitante(monkeypatch)
    dados.definir_proximo_contato(1, date(2026, 11, 20))   # atrasado
    dados.definir_proximo_contato(2, date(2026, 11, 30))   # futuro

    pendentes = dados.leads_para_contatar(dados.listar_leads(), hoje=date(2026, 11, 22))

    assert [lead.id for lead in pendentes] == [1]


def test_lead_fechado_nao_aparece_para_contatar(monkeypatch):
    sessao_de_visitante(monkeypatch)
    dados.definir_proximo_contato(1, date(2026, 11, 20))
    dados.atualizar_status(1, "Ganho")

    assert dados.leads_para_contatar(dados.listar_leads(), hoje=date(2026, 11, 22)) == []


def test_limpar_proximo_contato(monkeypatch):
    sessao_de_visitante(monkeypatch)
    dados.definir_proximo_contato(1, date(2026, 11, 20))

    dados.definir_proximo_contato(1, None)

    assert dados.buscar_lead(1).proximo_contato == ""


def test_excluir_conta_exige_login(monkeypatch):
    sessao_de_visitante(monkeypatch)

    with pytest.raises(ValueError):
        dados.excluir_conta()


def test_excluir_conta_de_email_apaga_dados_e_cadastro(monkeypatch):
    usuario = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email", "id": "uuid-1"}
    chamadas = []
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "excluir_dados_da_conta", lambda dono: chamadas.append(("dados", dono)) or 3)
    monkeypatch.setattr(dados.supabase_db, "excluir_usuario_do_login", lambda id_: chamadas.append(("login", id_)))

    assert dados.excluir_conta() == 3
    assert chamadas == [("dados", "ana@empresa.com"), ("login", "uuid-1")]


def test_excluir_conta_do_github_nao_mexe_no_login(monkeypatch):
    usuario = {"dono": "github|1", "email": "", "nome": "ana-dev", "provedor": "github"}
    chamadas = []
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "excluir_dados_da_conta", lambda dono: chamadas.append(dono) or 0)
    monkeypatch.setattr(
        dados.supabase_db, "excluir_usuario_do_login", lambda id_: pytest.fail("Não deveria apagar login externo")
    )

    dados.excluir_conta()

    assert chamadas == ["github|1"]



# ---------- Limites diários da IA, guardados no servidor ----------

HOJE = date(2026, 11, 22)
AMANHA = date(2026, 11, 23)


def usar_ia_ate_o_limite_da_sessao(hoje=HOJE):
    while dados.pode_usar_ia(hoje):
        dados.registrar_uso_ia(hoje)


def test_nova_sessao_nao_zera_o_limite_diario_da_demonstracao(monkeypatch):
    # Cada visitante (ou cada F5) é uma sessão nova, com o contador da sessão zerado
    visitantes = 0
    while True:
        sessao_de_visitante(monkeypatch, {})
        if not dados.pode_usar_ia(HOJE):
            break
        usar_ia_ate_o_limite_da_sessao()
        visitantes += 1

    total = dados._contador_do_servidor()["usos"][dados.CHAVE_DEMO_GLOBAL]
    assert total == dados.LIMITE_IA_DEMO_POR_DIA
    assert visitantes == -(-dados.LIMITE_IA_DEMO_POR_DIA // dados.LIMITE_IA_DEMO)  # divisão arredondada para cima
    assert "acabaram por hoje" in dados.aviso_limite_ia()


def test_limite_da_demonstracao_renova_no_dia_seguinte(monkeypatch):
    for _ in range(dados.LIMITE_IA_DEMO_POR_DIA):
        sessao_de_visitante(monkeypatch, {})
        dados.registrar_uso_ia(HOJE)

    sessao_de_visitante(monkeypatch, {})
    assert dados.pode_usar_ia(HOJE) is False
    assert dados.pode_usar_ia(AMANHA) is True


def test_limite_diario_por_conta(monkeypatch):
    ana = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: ana)
    monkeypatch.setattr(dados, "_sessao", dict)  # cada chamada parece uma sessão nova

    for _ in range(dados.LIMITE_IA_CONTA_POR_DIA):
        assert dados.pode_usar_ia(HOJE) is True
        dados.registrar_uso_ia(HOJE)

    assert dados.pode_usar_ia(HOJE) is False
    assert "20 análises com IA por dia" in dados.aviso_limite_ia()
    assert dados.pode_usar_ia(AMANHA) is True


def test_limite_de_uma_conta_nao_afeta_outra(monkeypatch):
    ana = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    bruno = {"dono": "github|2", "email": "", "nome": "bruno", "provedor": "github"}
    monkeypatch.setattr(dados, "_sessao", dict)

    monkeypatch.setattr(dados, "usuario_atual", lambda: ana)
    for _ in range(dados.LIMITE_IA_CONTA_POR_DIA):
        dados.registrar_uso_ia(HOJE)
    assert dados.pode_usar_ia(HOJE) is False

    monkeypatch.setattr(dados, "usuario_atual", lambda: bruno)
    assert dados.pode_usar_ia(HOJE) is True


def test_uso_da_demonstracao_nao_conta_para_as_contas(monkeypatch):
    for _ in range(dados.LIMITE_IA_DEMO_POR_DIA):
        sessao_de_visitante(monkeypatch, {})
        dados.registrar_uso_ia(HOJE)

    ana = {"dono": "ana@empresa.com", "email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: ana)
    assert dados.pode_usar_ia(HOJE) is True
