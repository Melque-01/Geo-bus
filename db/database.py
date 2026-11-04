"""Acesso ao PostgreSQL/PostGIS.

Uma conexão por chamada, sempre fechada (contextlib.closing) — o contexto
de conexão do psycopg apenas controla a transação, não fecha a conexão.
SQL sempre parametrizado (`%s`).
"""

import os
from contextlib import closing

import psycopg
from psycopg.rows import dict_row

from config import BANCO

CAMINHO_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def conectar():
    """Abre uma conexão com o banco configurado em `config.BANCO`."""
    return psycopg.connect(**BANCO, row_factory=dict_row)


def consultar(sql, parametros=()):
    """Executa um SELECT e devolve uma lista de dicionários."""
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


def consultar_um(sql, parametros=()):
    """Executa um SELECT e devolve o primeiro registro (ou None)."""
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchone()


def executar(sql, parametros=()):
    """Executa INSERT/UPDATE/DELETE e devolve o número de linhas afetadas."""
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        conexao.commit()
        return cursor.rowcount


def inserir(sql, parametros=()):
    """Executa um INSERT ... RETURNING id e devolve o id gerado."""
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        linha = cursor.fetchone()
        conexao.commit()
        return linha["id"] if linha else None


def disponivel():
    """Verifica se o banco responde (healthcheck / mensagens de erro)."""
    try:
        consultar_um("SELECT 1 AS ok")
        return True
    except Exception:  # noqa: BLE001 - qualquer falha = indisponível
        return False


def criar_tabelas():
    """Aplica `db/schema.sql` (idempotente)."""
    with open(CAMINHO_SCHEMA, encoding="utf-8") as arquivo:
        script = arquivo.read()

    comandos = [c.strip() for c in script.split(";") if c.strip()]
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        for comando in comandos:
            cursor.execute(comando)
        conexao.commit()
