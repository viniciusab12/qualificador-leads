from src.componentes import texto_seguro, texto_seguro_com_linhas


def test_link_aparece_como_texto():
    texto = texto_seguro("[Clique aqui](https://site-falso.com)")

    assert "\\[" in texto and "\\]" in texto and "\\(" in texto
    assert "https\\:\\/\\/" in texto


def test_imagem_e_negrito_nao_sao_interpretados():
    assert texto_seguro("![](https://x.com/a.png)").startswith("\\!\\[")
    assert texto_seguro("**forte**") == "\\*\\*forte\\*\\*"


def test_texto_comum_nao_muda():
    assert texto_seguro("Padaria Vida 2026") == "Padaria Vida 2026"


def test_texto_com_linhas_mantem_as_quebras():
    texto = texto_seguro_com_linhas("Resumo: ok\n- [link](x)")

    assert texto == "Resumo\\: ok  \n\\- \\[link\\]\\(x\\)"
