"""Teste de reconciliacao (Parte 4, item 2).

Compara a ORIGEM (dados brutos salvos em brutos/pedidos.json) com o DESTINO
(tabela pedidos no PostgreSQL), depois que o ETL ja rodou:

1. contagem de pedidos unicos da origem == contagem na tabela pedidos;
2. soma de valor_itens da origem == soma de valor_itens no destino (tolerancia de 1 centavo).

A origem e calculada aqui de forma independente (sem reutilizar as funcoes do ETL),
para que o teste nao concorde com um erro do proprio codigo.

Pre-requisito: rode o ETL (python -m etl.main) antes do pytest.
"""
import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PEDIDOS = RAIZ / "brutos" / "pedidos.json"
TOLERANCIA = Decimal("0.01")


# ---------- configuracao do banco (le o .env sem biblioteca extra) ----------

def _carregar_env():
    caminho = RAIZ / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _env(*nomes, padrao=None):
    for nome in nomes:
        if os.environ.get(nome):
            return os.environ[nome]
    return padrao


def _conectar():
    _carregar_env()
    return psycopg.connect(
        host=_env("DB_HOST", "PGHOST", padrao="localhost"),
        port=_env("DB_PORT", "PGPORT", padrao="5432"),
        dbname=_env("DB_NAME", "PGDATABASE", padrao="verdejar"),
        user=_env("DB_USER", "PGUSER", padrao="postgres"),
        password=_env("DB_PASSWORD", "PGPASSWORD"),
    )


# ---------- calculo da origem ----------

def _para_decimal(valor):
    """Aceita numero ou texto com virgula decimal (ex.: '3,50')."""
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return Decimal(str(valor))


def _origem():
    """Devolve (qtd_pedidos_unicos, soma_valor_itens) a partir dos dados brutos."""
    if not ARQUIVO_PEDIDOS.exists():
        pytest.skip(f"{ARQUIVO_PEDIDOS} nao existe: rode o ETL antes do pytest")

    pedidos = json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8"))

    unicos = {}
    for pedido in pedidos:
        unicos.setdefault(pedido["id"], pedido)  # mantem a primeira ocorrencia

    soma = Decimal("0")
    for pedido in unicos.values():
        for item in pedido["itens"]:
            soma += _para_decimal(item["quantidade"]) * _para_decimal(item["preco_unitario"])

    return len(unicos), soma


# ---------- consulta ao destino ----------

def _destino():
    """Devolve (qtd_pedidos, soma_valor_itens) da tabela pedidos."""
    try:
        conexao = _conectar()
    except psycopg.OperationalError as erro:
        pytest.skip(f"sem conexao com o banco: {erro}")

    with conexao:
        with conexao.cursor() as cur:
            cur.execute("SELECT COUNT(*), COALESCE(SUM(valor_itens), 0) FROM pedidos")
            quantidade, soma = cur.fetchone()
    return quantidade, Decimal(str(soma))


# ---------- testes ----------

def test_reconciliacao_contagem_de_pedidos():
    qtd_origem, _ = _origem()
    qtd_destino, _ = _destino()
    assert qtd_destino == qtd_origem


def test_reconciliacao_soma_de_valor_itens():
    _, soma_origem = _origem()
    _, soma_destino = _destino()
    diferenca = abs(soma_origem - soma_destino)
    assert diferenca <= TOLERANCIA, (
        f"origem={soma_origem:.2f} destino={soma_destino:.2f} diferenca={diferenca:.2f}"
    )