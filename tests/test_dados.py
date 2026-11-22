import pytest

from src import dados


def test_sem_login_usa_base_de_demonstracao(monkeypatch):
    monkeypatch.setattr(dados, "usuario_atual", lambda: None)
    monkeypatch.setattr(dados.demo, "listar_leads", lambda: ["lead de demonstração"])
    monkeypatch.setattr(dados.supabase_db, "listar_leads", lambda email: ["lead do usuário"])

    assert dados.listar_leads() == ["lead de demonstração"]
    assert dados.modo_demonstracao() is True


def test_com_login_usa_os_leads_do_usuario(monkeypatch):
    usuario = {"email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", lambda email: [f"leads de {email}"])

    assert dados.listar_leads() == ["leads de ana@empresa.com"]
    assert dados.modo_demonstracao() is False


def test_falha_no_banco_vira_erro_banco(monkeypatch):
    def falhar(email):
        raise ConnectionError("sem internet")

    usuario = {"email": "ana@empresa.com", "nome": "Ana", "provedor": "email"}
    monkeypatch.setattr(dados, "usuario_atual", lambda: usuario)
    monkeypatch.setattr(dados.supabase_db, "listar_leads", falhar)

    with pytest.raises(dados.ErroBanco):
        dados.listar_leads()


def test_status_invalido_continua_como_value_error(monkeypatch):
    monkeypatch.setattr(dados, "usuario_atual", lambda: None)

    with pytest.raises(ValueError):
        dados.atualizar_status(1, "Fechadoo")
