"""Relatorio de qualidade (Stretch): contadores de cada armadilha, por execucao.

A cada execucao do ETL, acrescenta ao arquivo CSV uma linha por armadilha (A1 a A6),
todas com a mesma data e hora. O arquivo nunca e apagado: cada execucao fica registrada
no historico. Rodar o ETL duas vezes gera 12 linhas de dados (6 por execucao); isso nao
afeta a idempotencia do banco, que e uma garantia da carga, nao do relatorio.

Colunas:
  data_hora       data e hora da execucao (ISO 8601, com fuso), igual nas 6 linhas
  armadilha       codigo A1 a A6
  descricao       o que o ETL tratou
  contador        quantos registros foram tratados
  total_avaliado  quantos registros foram examinados (para dar proporcao ao contador)

Este modulo nao depende dos outros modulos do ETL: recebe os contadores prontos.
"""

import csv
import os
from datetime import datetime

CAMINHO_PADRAO = os.path.join("relatorios", "relatorio_qualidade.csv")
COLUNAS = ["data_hora", "armadilha", "descricao", "contador", "total_avaliado"]

# (codigo, de onde vem o contador, descricao, base de comparacao)
# origem do contador: "c" = contadores de clientes, "p" = contadores de pedidos
# base: "clientes", "pedidos_unicos" ou "pedidos_brutos"
ARMADILHAS = [
    ("A1", "c", "emails_nulos", "e-mail ausente gravado como nulo", "clientes"),
    ("A2", "c", "estados_padronizados", "sigla de estado corrigida para maiusculas", "clientes"),
    ("A3", "p", "datas_convertidas", "data convertida de DD/MM/AAAA para AAAA-MM-DD", "pedidos_unicos"),
    ("A4", "p", "valores_convertidos", "valor_total em texto com virgula convertido para numero", "pedidos_unicos"),
    ("A5", "p", "repetidos_descartados", "pedido repetido descartado", "pedidos_brutos"),
    ("A6", "p", "divergentes", "pedido com valor_total diferente da soma dos itens", "pedidos_unicos"),
]


def montar_linhas(data_hora, contadores_clientes, contadores_pedidos, n_clientes, n_pedidos_brutos):
    """Monta as 6 linhas do relatorio (uma por armadilha). Funcao pura, sem escrita em disco."""
    bases = {
        "clientes": n_clientes,
        "pedidos_brutos": n_pedidos_brutos,
        "pedidos_unicos": contadores_pedidos["pedidos_unicos"],
    }
    fontes = {"c": contadores_clientes, "p": contadores_pedidos}

    linhas = []
    for codigo, fonte, chave, descricao, base in ARMADILHAS:
        linhas.append(
            {
                "data_hora": data_hora,
                "armadilha": codigo,
                "descricao": descricao,
                "contador": fontes[fonte][chave],
                "total_avaliado": bases[base],
            }
        )
    return linhas


def gravar_relatorio(linhas, caminho=CAMINHO_PADRAO):
    """Acrescenta as linhas ao CSV, criando a pasta e o cabecalho se ainda nao existirem."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    escrever_cabecalho = not os.path.isfile(caminho) or os.path.getsize(caminho) == 0
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        if escrever_cabecalho:
            escritor.writeheader()
        escritor.writerows(linhas)


def gerar_relatorio(
    contadores_clientes,
    contadores_pedidos,
    n_clientes,
    n_pedidos_brutos,
    caminho=CAMINHO_PADRAO,
    agora=None,
):
    """Monta e grava o relatorio da execucao atual. Devolve as linhas gravadas.

    'agora' existe so para os testes fixarem a data e hora; no ETL fica em None.
    """
    if agora is None:
        agora = datetime.now().astimezone()
    data_hora = agora.isoformat(timespec="seconds")

    linhas = montar_linhas(
        data_hora, contadores_clientes, contadores_pedidos, n_clientes, n_pedidos_brutos
    )
    gravar_relatorio(linhas, caminho)
    print(f"relatorio: arquivo={caminho} data_hora={data_hora} armadilhas={len(linhas)}")
    return linhas
