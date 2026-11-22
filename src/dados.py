"""Escolhe de onde vêm os leads e as regras de pontuação.

Visitante sem login: os 50 leads de exemplo (SQLite) mais as mudanças que
esse visitante fez, guardadas só na sessão dele (st.session_state).
Usuário logado: os próprios leads e regras, no Supabase.
As páginas usam só este módulo, sem saber qual banco está por trás.
"""

from dataclasses import replace
from datetime import date, datetime

import streamlit as st

from src import criterios as regras
from src import database as demo
from src import supabase_db
from src.auth import usuario_atual
from src.models import STATUS_EM_ABERTO, STATUS_FUNIL
from src.scoring import calcular_pontuacao

# Quantas análises reais do Gemini cada visitante pode pedir no modo demonstração
LIMITE_IA_DEMO = 3

# Tamanho máximo de uma anotação
MAXIMO_ANOTACAO = 500

# Chaves da sessão do visitante no modo demonstração
CHAVE_NOVOS = "demo_leads_novos"          # leads que o visitante cadastrou
CHAVE_EDICOES = "demo_leads_editados"     # {id do lead: {campo: novo valor}}
CHAVE_EXCLUIDOS = "demo_leads_excluidos"  # ids que o visitante excluiu
CHAVE_USO_IA = "demo_analises_ia"         # quantas análises reais já pediu
CHAVE_CRITERIOS = "demo_criterios"        # versões das regras que o visitante salvou

# Os mesmos campos que o Supabase aceita alterar
CAMPOS_EDITAVEIS = supabase_db.CAMPOS_EDITAVEIS


class ErroBanco(Exception):
    """Falha ao ler ou gravar leads, em qualquer um dos bancos."""


def email_logado():
    """Dono dos leads de quem está logado, ou None no modo demonstração.

    Para e-mail e senha e para o Google, é o e-mail. Para o GitHub, é o
    identificador fixo da conta (ex.: "github|12345").
    """
    usuario = usuario_atual()
    return usuario["dono"] if usuario else None


def modo_demonstracao():
    """True quando ninguém está logado."""
    return email_logado() is None


def _conferir_campos(campos):
    """Recusa campos que não podem mudar e status fora do funil (vale para os dois bancos)."""
    desconhecidos = set(campos) - CAMPOS_EDITAVEIS
    if desconhecidos:
        raise ValueError(f"Campos que não podem ser alterados: {sorted(desconhecidos)}")
    if "status" in campos and campos["status"] not in STATUS_FUNIL:
        raise ValueError(f"Status inválido: {campos['status']}. Use um destes: {STATUS_FUNIL}")


# ---------- Modo demonstração: mudanças só na sessão do visitante ----------
#
# O arquivo SQLite com os 50 leads de exemplo é compartilhado por todos os
# visitantes. Por isso ele só é lido, nunca alterado. O que cada visitante
# cadastra, muda ou exclui fica guardado na sessão dele e some quando a aba fecha.

def _sessao():
    """Onde ficam as mudanças do visitante. Os testes trocam por um dicionário."""
    return st.session_state


def _demo_listar():
    sessao = _sessao()
    excluidos = sessao.get(CHAVE_EXCLUIDOS, set())
    edicoes = sessao.get(CHAVE_EDICOES, {})

    exemplos = [
        replace(lead, **edicoes.get(lead.id, {}))
        for lead in demo.listar_leads()
        if lead.id not in excluidos
    ]
    novos = [replace(lead, **edicoes.get(lead.id, {})) for lead in sessao.get(CHAVE_NOVOS, [])]
    # Mais novos primeiro, como no banco
    return sorted(novos, key=lambda lead: lead.id, reverse=True) + exemplos


def _demo_buscar(lead_id):
    lead_id = int(lead_id)
    for lead in _demo_listar():
        if lead.id == lead_id:
            return lead
    return None


def _demo_salvar(lead):
    sessao = _sessao()
    novos = sessao.setdefault(CHAVE_NOVOS, [])

    ids_usados = [item.id for item in demo.listar_leads()] + [item.id for item in novos]
    novo_id = max(ids_usados, default=0) + 1

    novos.append(
        replace(lead, id=novo_id, criado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    return novo_id


def _demo_atualizar_campos(lead_id, campos):
    _conferir_campos(campos)
    lead_id = int(lead_id)
    if _demo_buscar(lead_id) is None:
        return False
    _sessao().setdefault(CHAVE_EDICOES, {}).setdefault(lead_id, {}).update(campos)
    return True


def _demo_atualizar_status(lead_id, novo_status):
    return _demo_atualizar_campos(lead_id, {"status": novo_status})


def _demo_excluir(lead_id):
    lead_id = int(lead_id)
    if _demo_buscar(lead_id) is None:
        return False

    sessao = _sessao()
    novos = sessao.get(CHAVE_NOVOS, [])
    if any(lead.id == lead_id for lead in novos):
        sessao[CHAVE_NOVOS] = [lead for lead in novos if lead.id != lead_id]
    else:
        sessao.setdefault(CHAVE_EXCLUIDOS, set()).add(lead_id)
    return True


def _demo_buscar_criterios():
    versoes = _sessao().get(CHAVE_CRITERIOS, [])
    return versoes[-1] if versoes else None


def _demo_salvar_criterios(config):
    versoes = _sessao().setdefault(CHAVE_CRITERIOS, [])
    nova_versao = len(versoes) + 1
    versoes.append({**config, "versao": nova_versao})
    return nova_versao


def pode_usar_ia():
    """Logado: sempre. Modo demonstração: até LIMITE_IA_DEMO análises por visitante."""
    if not modo_demonstracao():
        return True
    return _sessao().get(CHAVE_USO_IA, 0) < LIMITE_IA_DEMO


def registrar_uso_ia():
    """Conta uma análise real feita no modo demonstração."""
    if modo_demonstracao():
        sessao = _sessao()
        sessao[CHAVE_USO_IA] = sessao.get(CHAVE_USO_IA, 0) + 1


# ---------- Escolha do banco ----------

def _executar(funcao_demo, funcao_usuario, *args):
    """Chama a função do banco certo e padroniza os erros."""
    email = email_logado()
    try:
        if email:
            return funcao_usuario(*args, email)
        return funcao_demo(*args)
    except ValueError:
        raise
    except Exception as erro:
        raise ErroBanco(str(erro)) from erro


def criar_tabela():
    """Prepara a base de demonstração. No Supabase, a tabela já existe."""
    demo.criar_tabela()


def listar_leads():
    return _executar(_demo_listar, supabase_db.listar_leads)


def buscar_lead(lead_id):
    return _executar(_demo_buscar, supabase_db.buscar_lead, lead_id)


def salvar_lead(lead):
    return _executar(_demo_salvar, supabase_db.salvar_lead, lead)


def atualizar_status(lead_id, novo_status):
    return _executar(_demo_atualizar_status, supabase_db.atualizar_status, lead_id, novo_status)


def atualizar_campos(lead_id, campos):
    """Muda campos de um lead (só os de CAMPOS_EDITAVEIS). Devolve True se encontrou o lead."""
    _conferir_campos(campos)
    return _executar(_demo_atualizar_campos, supabase_db.atualizar_campos, lead_id, campos)


def excluir_lead(lead_id):
    return _executar(_demo_excluir, supabase_db.excluir_lead, lead_id)


# ---------- Regras de pontuação ----------

def buscar_criterios():
    """Regras da conta (ou do visitante). Sem personalização, devolve as regras padrão."""
    config = _executar(_demo_buscar_criterios, supabase_db.buscar_criterios)
    return regras.completar_criterios(config)


def salvar_criterios(config):
    """Valida e guarda uma versão nova das regras. Devolve o número da versão.

    Configuração inválida gera ValueError com os erros, um por linha.
    """
    config = regras.completar_criterios(config)
    erros = regras.validar_criterios(config)
    if erros:
        raise ValueError("\n".join(erros))
    return _executar(_demo_salvar_criterios, supabase_db.salvar_criterios, config)


def pontuar(lead, config=None):
    """Calcula a nota com as regras da conta e grava o resultado no próprio lead."""
    resultado = calcular_pontuacao(lead, config or buscar_criterios())
    lead.nota = resultado["nota"]
    lead.classificacao = resultado["classificacao"]
    lead.justificativa = resultado["justificativa"]
    lead.criterios_versao = resultado["criterios_versao"]
    return lead


def campos_da_pontuacao(lead):
    """Os campos que mudam quando a nota é recalculada."""
    return {
        "nota": lead.nota,
        "classificacao": lead.classificacao,
        "justificativa": lead.justificativa,
        "criterios_versao": lead.criterios_versao,
    }


def recalcular_todos():
    """Aplica as regras atuais em todos os leads. Devolve quantos mudaram de nota ou classificação."""
    config = buscar_criterios()
    alterados = 0
    for lead in listar_leads():
        antes = (lead.nota, lead.classificacao)
        pontuar(lead, config)
        atualizar_campos(lead.id, campos_da_pontuacao(lead))
        if (lead.nota, lead.classificacao) != antes:
            alterados += 1
    return alterados


# ---------- Acompanhamento ----------

def adicionar_anotacao(lead_id, texto, agora=None):
    """Acrescenta uma anotação com data e hora ao histórico do lead."""
    texto = texto.strip()[:MAXIMO_ANOTACAO]
    if not texto:
        raise ValueError("Escreva a anotação antes de salvar.")
    lead = buscar_lead(lead_id)
    if lead is None:
        return False
    agora = agora or datetime.now()
    nova = {"data": agora.strftime("%Y-%m-%d %H:%M"), "texto": texto}
    return atualizar_campos(lead_id, {"anotacoes": list(lead.anotacoes) + [nova]})


def definir_proximo_contato(lead_id, data):
    """Marca (ou limpa, com None) a data do próximo contato."""
    valor = data.isoformat() if data else ""
    return atualizar_campos(lead_id, {"proximo_contato": valor})


def leads_para_contatar(leads, hoje=None):
    """Leads em aberto com próximo contato marcado para hoje ou para antes (atrasados)."""
    hoje = (hoje or date.today()).isoformat()
    pendentes = [
        lead
        for lead in leads
        if lead.proximo_contato and lead.proximo_contato <= hoje and lead.status in STATUS_EM_ABERTO
    ]
    return sorted(pendentes, key=lambda lead: lead.proximo_contato)


# ---------- Conta ----------

def excluir_conta():
    """Apaga todos os leads e regras da conta logada. Devolve quantos leads foram apagados.

    Para quem entrou com e-mail e senha, também apaga o cadastro no Supabase Auth.
    Quem chama esta função deve fazer o logout em seguida.
    """
    usuario = usuario_atual()
    if usuario is None:
        raise ValueError("Entre na sua conta para excluí-la.")
    try:
        apagados = supabase_db.excluir_dados_da_conta(usuario["dono"])
        if usuario["provedor"] == "email" and usuario.get("id"):
            supabase_db.excluir_usuario_do_login(usuario["id"])
    except Exception as erro:
        raise ErroBanco(str(erro)) from erro
    return apagados
