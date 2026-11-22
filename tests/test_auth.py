from src.auth import traduzir_erro, validar_credenciais


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
