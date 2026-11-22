import pytest

from src import auth
from src.auth import (
    NOME_COOKIE,
    dono_do_login_externo,
    normalizar_email,
    provedor_do_login_externo,
    token_do_cookie,
    traduzir_erro,
    validar_credenciais,
)

EMISSOR_GOOGLE = "https://accounts.google.com"
EMISSOR_AUTH0 = "https://dev-exemplo.us.auth0.com/"



def test_credenciais_validas():
    assert validar_credenciais("ana@empresa.com", "segredo1") == []


def test_email_invalido():
    erros = validar_credenciais("ana.empresa.com", "segredo1")

    assert "Informe um e-mail válido." in erros


def test_senha_nova_precisa_de_8_caracteres():
    erros = validar_credenciais("ana@empresa.com", "1234567")

    assert "A senha precisa ter pelo menos 8 caracteres." in erros
    assert validar_credenciais("ana@empresa.com", "12345678") == []


def test_entrar_aceita_senha_antiga_de_6_caracteres():
    assert validar_credenciais("ana@empresa.com", "123456", senha_nova=False) == []


def test_entrar_exige_senha_preenchida():
    assert "Informe a senha." in validar_credenciais("ana@empresa.com", "", senha_nova=False)


def test_traduz_erros_conhecidos_do_supabase():
    assert traduzir_erro(Exception("Invalid login credentials")) == "E-mail ou senha incorretos."
    assert "Confirme o seu e-mail" in traduzir_erro(Exception("Email not confirmed"))
    assert "Já existe uma conta" in traduzir_erro(Exception("User already registered"))


def test_erro_desconhecido_vira_mensagem_generica():
    assert "Tente novamente" in traduzir_erro(Exception("erro estranho 500"))


def test_traduz_erros_da_recuperacao_de_senha():
    assert "Código inválido" in traduzir_erro(Exception("Token has expired or is invalid"))
    assert "diferente" in traduzir_erro(Exception("New password should be different from the old password."))


def test_token_do_cookie():
    assert token_do_cookie({NOME_COOKIE: "abc123"}) == "abc123"
    assert token_do_cookie({NOME_COOKIE: "  "}) is None
    assert token_do_cookie({}) is None
    assert token_do_cookie(None) is None


# ---------- Dono dos leads no login com Google e GitHub ----------

def test_identifica_o_provedor_pelo_emissor():
    assert provedor_do_login_externo({"iss": EMISSOR_AUTH0}) == "github"
    assert provedor_do_login_externo({"iss": EMISSOR_GOOGLE}) == "google"


def test_github_usa_o_sub_mesmo_com_email():
    dados = {"iss": EMISSOR_AUTH0, "sub": "github|12345", "email": "ana@empresa.com", "email_verified": True}

    assert dono_do_login_externo(dados) == "github|12345"


def test_github_sem_email_usa_o_sub():
    dados = {"iss": EMISSOR_AUTH0, "sub": "github|12345"}

    assert dono_do_login_externo(dados) == "github|12345"


def test_auth0_com_outra_conexao_e_recusado():
    # Conta criada com e-mail e senha no próprio Auth0: o e-mail não pode virar dono
    dados = {"iss": EMISSOR_AUTH0, "sub": "auth0|abc", "email": "ana@empresa.com", "email_verified": False}

    assert dono_do_login_externo(dados) is None


def test_google_com_email_verificado():
    dados = {"iss": EMISSOR_GOOGLE, "sub": "1093", "email": "Ana@Empresa.com", "email_verified": True}

    assert dono_do_login_externo(dados) == "ana@empresa.com"


def test_google_com_email_nao_verificado_e_recusado():
    dados = {"iss": EMISSOR_GOOGLE, "sub": "1093", "email": "ana@empresa.com", "email_verified": False}

    assert dono_do_login_externo(dados) is None


def test_google_sem_informacao_de_verificacao_e_recusado():
    dados = {"iss": EMISSOR_GOOGLE, "sub": "1093", "email": "ana@empresa.com"}

    assert dono_do_login_externo(dados) is None


def test_normalizar_email():
    assert normalizar_email("  Ana@Empresa.COM ") == "ana@empresa.com"
    assert normalizar_email(None) == ""


# ---------- Limite de tentativas de login ----------

@pytest.fixture
def sessao(monkeypatch):
    dicionario = {}
    monkeypatch.setattr(auth, "_sessao", lambda: dicionario)
    return dicionario


def test_bloqueia_depois_de_5_senhas_erradas(sessao):
    for segundo in range(auth.MAXIMO_FALHAS - 1):
        auth.registrar_falha_de_login(agora=1000 + segundo)
    assert auth.segundos_de_bloqueio(agora=1010) == 0

    auth.registrar_falha_de_login(agora=1010)

    assert auth.segundos_de_bloqueio(agora=1010) == auth.BLOQUEIO_SEGUNDOS


def test_bloqueio_acaba_depois_do_tempo(sessao):
    for _ in range(auth.MAXIMO_FALHAS):
        auth.registrar_falha_de_login(agora=1000)

    assert auth.segundos_de_bloqueio(agora=1000 + auth.BLOQUEIO_SEGUNDOS) == 0


def test_contagem_recomeca_depois_do_bloqueio(sessao):
    for _ in range(auth.MAXIMO_FALHAS):
        auth.registrar_falha_de_login(agora=1000)
    depois = 1000 + auth.BLOQUEIO_SEGUNDOS + 1

    auth.registrar_falha_de_login(agora=depois)

    assert auth.segundos_de_bloqueio(agora=depois) == 0


def test_login_bloqueado_nem_chama_o_supabase(sessao, monkeypatch):
    def proibido():
        raise AssertionError("O Supabase não deveria ser chamado durante o bloqueio")

    monkeypatch.setattr(auth, "_cliente_auth", proibido)
    for _ in range(auth.MAXIMO_FALHAS):
        auth.registrar_falha_de_login()

    sucesso, mensagem = auth.entrar_com_email("ana@empresa.com", "senha-errada")

    assert sucesso is False
    assert "Muitas tentativas" in mensagem


def test_senha_errada_conta_como_falha(sessao, monkeypatch):
    class ClienteFalso:
        class auth:
            @staticmethod
            def sign_in_with_password(dados):
                raise Exception("Invalid login credentials")

    monkeypatch.setattr(auth, "_cliente_auth", lambda: ClienteFalso)

    sucesso, mensagem = auth.entrar_com_email("ana@empresa.com", "senha-errada")

    assert sucesso is False
    assert mensagem == "E-mail ou senha incorretos."
    assert len(sessao[auth.CHAVE_FALHAS]) == 1
