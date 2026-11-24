"""Carga no PostgreSQL (caminho A): produtos, clientes, pedidos e itens_pedido.

Idempotencia: TRUNCATE ... CASCADE dentro da mesma transacao da carga.
Se qualquer insercao falhar, o rollback restaura o estado anterior do banco.
Todas as insercoes usam parametros (nunca SQL concatenado com dados).
"""

import os
from decimal import Decimal, ROUND_HALF_UP

import psycopg

CENTAVO = Decimal("0.01")


# ---------------------------------------------------------------- conexao
def _localizar_env():
    """Procura o .env na pasta atual e nas pastas acima deste arquivo (raiz do projeto)."""
    inicio = os.path.dirname(os.path.abspath(__file__))
    candidatos = [os.path.join(os.getcwd(), ".env")]
    pasta = inicio
    for _ in range(4):
        candidatos.append(os.path.join(pasta, ".env"))
        pasta = os.path.dirname(pasta)
    for caminho in candidatos:
        if os.path.isfile(caminho):
            return caminho
    return None


def _carregar_env():
    """Le o .env (CHAVE=valor) para os.environ, sem sobrescrever o que ja existe."""
    caminho = _localizar_env()
    if caminho is None:
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            if linha.startswith("export "):
                linha = linha[len("export "):]
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _env(nomes, padrao=""):
    """Devolve o valor da primeira variavel definida entre os nomes aceitos."""
    for nome in nomes:
        valor = os.environ.get(nome)
        if valor:
            return valor
    return padrao


def conectar():
    """Abre a conexao com o PostgreSQL usando o .env da raiz do projeto.

    Nomes aceitos para cada informacao:
      host: PGHOST, DB_HOST, POSTGRES_HOST
      porta: PGPORT, DB_PORT, POSTGRES_PORT
      banco: PGDATABASE, DB_NAME, POSTGRES_DB
      usuario: PGUSER, DB_USER, POSTGRES_USER
      senha: PGPASSWORD, DB_PASSWORD, DB_PASS, POSTGRES_PASSWORD
    """
    _carregar_env()
    try:
        return psycopg.connect(
            host=_env(["PGHOST", "DB_HOST", "POSTGRES_HOST"], "localhost"),
            port=_env(["PGPORT", "DB_PORT", "POSTGRES_PORT"], "5432"),
            dbname=_env(["PGDATABASE", "DB_NAME", "POSTGRES_DB"], "verdejar"),
            user=_env(["PGUSER", "DB_USER", "POSTGRES_USER"], "postgres"),
            password=_env(["PGPASSWORD", "DB_PASSWORD", "DB_PASS", "POSTGRES_PASSWORD"]),
        )
    except psycopg.OperationalError as erro:
        # A mensagem do erro nao inclui a senha.
        print(f"carga: erro de conexao com o banco: {erro}")
        return None


# ---------------------------------------------------------------- conversoes
def _dec(valor):
    """Converte numero ou texto com virgula decimal em Decimal com 2 casas."""
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _itens_do_pedido(pedido):
    """Devolve a lista de itens aninhados no pedido (chave 'itens')."""
    return pedido.get("itens") or []


def _valor_itens(pedido):
    """valor_itens ja calculado na transformacao; se faltar, soma os itens."""
    if pedido.get("valor_itens") is not None:
        return _dec(pedido["valor_itens"])
    return sum(
        (int(i["quantidade"]) * _dec(i["preco_unitario"]) for i in _itens_do_pedido(pedido)),
        Decimal("0.00"),
    )


# ---------------------------------------------------------------- montagem das linhas
def _linhas_produtos(produtos):
    return [
        (int(p["produto_id"]), p["nome"], p["categoria"], _dec(p["preco_base"]))
        for p in produtos
    ]


def _linhas_clientes(clientes):
    return [
        (
            int(c["id"]),
            c["nome"],
            c.get("email") or None,  # A1: vazio vira NULL
            c["cidade"],
            c["estado"],
            c["cadastro_em"],
        )
        for c in clientes
    ]


def _linhas_pedidos(pedidos):
    return [
        (
            int(p["id"]),
            int(p["cliente_id"]),
            p["data_pedido"],
            p["status"],
            _dec(p["valor_total"]),
            _valor_itens(p),
            bool(p["divergente"]),
        )
        for p in pedidos
    ]


def _linhas_itens(pedidos):
    linhas = []
    for p in pedidos:
        for posicao, item in enumerate(_itens_do_pedido(p), start=1):
            linhas.append(
                (
                    int(p["id"]),
                    int(item.get("linha", posicao)),
                    int(item["produto_id"]),
                    int(item["quantidade"]),
                    _dec(item["preco_unitario"]),
                )
            )
    return linhas


# ---------------------------------------------------------------- carga
def carregar(produtos, clientes, pedidos):
    """Carrega tudo no banco em uma unica transacao e imprime a reconciliacao.

    Recebe os dados ja transformados. Devolve um dicionario com os totais
    (usado pelo teste de reconciliacao) ou None em caso de falha.
    """
    linhas_produtos = _linhas_produtos(produtos)
    linhas_clientes = _linhas_clientes(clientes)
    linhas_pedidos = _linhas_pedidos(pedidos)
    linhas_itens = _linhas_itens(pedidos)

    conn = conectar()
    if conn is None:
        return None

    try:
        # "with conn" confirma (commit) ao sair sem erro e desfaz (rollback) se houver excecao.
        with conn:
            with conn.cursor() as cur:
                # Idempotencia: limpa tudo antes de carregar, na mesma transacao.
                cur.execute(
                    "TRUNCATE itens_pedido, pedidos, clientes, produtos CASCADE"
                )

                # Ordem das chaves estrangeiras: produtos, clientes, pedidos, itens.
                cur.executemany(
                    "INSERT INTO produtos (produto_id, nome, categoria, preco_base) "
                    "VALUES (%s, %s, %s, %s)",
                    linhas_produtos,
                )
                cur.executemany(
                    "INSERT INTO clientes (id, nome, email, cidade, estado, cadastro_em) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    linhas_clientes,
                )
                cur.executemany(
                    "INSERT INTO pedidos (id, cliente_id, data_pedido, status, "
                    "valor_total, valor_itens, divergente) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    linhas_pedidos,
                )
                cur.executemany(
                    "INSERT INTO itens_pedido (pedido_id, linha, produto_id, "
                    "quantidade, preco_unitario) VALUES (%s, %s, %s, %s, %s)",
                    linhas_itens,
                )

                # Contagens e somas no destino, ainda dentro da transacao.
                cur.execute("SELECT COUNT(*) FROM produtos")
                n_produtos = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM clientes")
                n_clientes = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM pedidos")
                n_pedidos = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM itens_pedido")
                n_itens = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(valor_itens), 0) FROM pedidos")
                soma_destino = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM pedidos WHERE divergente")
                n_divergentes = cur.fetchone()[0]
    except psycopg.Error as erro:
        print(f"carga: erro ao gravar no banco, transacao desfeita: {erro}")
        return None
    finally:
        conn.close()

    soma_origem = sum((l[5] for l in linhas_pedidos), Decimal("0.00"))
    diferenca = abs(soma_origem - soma_destino)

    print(f"carga: clientes={n_clientes} produtos={n_produtos} pedidos={n_pedidos} itens={n_itens}")
    print(
        f"reconciliacao: soma_valor_itens_origem={soma_origem} "
        f"soma_valor_itens_destino={soma_destino} diferenca={diferenca}"
    )
    print(f"divergentes: {n_divergentes} pedidos com valor_total diferente da soma dos itens")

    return {
        "produtos": n_produtos,
        "clientes": n_clientes,
        "pedidos": n_pedidos,
        "itens": n_itens,
        "soma_origem": soma_origem,
        "soma_destino": soma_destino,
        "diferenca": diferenca,
        "divergentes": n_divergentes,
    }