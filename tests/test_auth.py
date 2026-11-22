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


def test_senha_curta():
    erros = validar_credenciais("ana@empresa.com", "123")

    assert "A senha precisa ter pelo menos 6 caracteres." in erros


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
