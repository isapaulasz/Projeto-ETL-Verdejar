# etl/extracao.py
import csv
import json
import os
import sys
import requests

BASE_URL = "http://127.0.0.1:8000"


def buscar_pagina(rota, pagina, tamanho=100):
    try:
        resp = requests.get(
            f"{BASE_URL}/{rota}",
            params={"page": pagina, "page_size": tamanho},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        print(f"ERRO: nao foi possivel conectar em {rota}. A API esta rodando?")
        return None
    except requests.exceptions.Timeout:
        print(f"ERRO: tempo esgotado ao buscar {rota} pagina {pagina}")
        return None
    except requests.exceptions.RequestException as erro:
        print(f"ERRO: falha de rede em {rota} pagina {pagina}: {erro}")
        return None

    if resp.status_code == 404:
        print(f"ERRO: {rota} pagina {pagina} nao existe")
        return None
    if resp.status_code != 200:
        print(f"ERRO: status {resp.status_code} em {rota} pagina {pagina}")
        return None

    try:
        return resp.json()
    except ValueError:
        print(f"ERRO: resposta de {rota} pagina {pagina} nao e JSON valido")
        return None


def extrair_tudo(rota, tamanho=100):
    registros = []
    pagina = 1
    total_paginas = 1  # sera atualizado pela 1a resposta

    while pagina <= total_paginas:
        dados = buscar_pagina(rota, pagina, tamanho)
        if dados is None:
            print(f"extracao: {rota} INCOMPLETA, falhou na pagina {pagina}")
            return None  # nunca devolver dados parciais

        total_paginas = dados["total_pages"]
        registros.extend(dados["items"])
        pagina += 1

    rotulo = "registros_brutos" if rota == "pedidos" else "registros"
    print(f"extracao: {rota} paginas={total_paginas} {rotulo}={len(registros)}")
    return registros


def salvar_brutos(rota, registros):
    os.makedirs("brutos", exist_ok=True)
    with open(f"brutos/{rota}.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)


def ler_csv(nome_arquivo):
    with open(f"insumos/dados/{nome_arquivo}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    clientes = extrair_tudo("clientes")
    pedidos = extrair_tudo("pedidos")
    if clientes is None or pedidos is None:
        sys.exit(1)

    salvar_brutos("clientes", clientes)
    salvar_brutos("pedidos", pedidos)

    produtos = ler_csv("produtos")
    print(f"extracao: produtos registros={len(produtos)}")


if __name__ == "__main__":
    main()