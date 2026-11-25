# Como usei IA neste projeto

A ferramenta utilizada foi o Claude (claude.ai). O papel definido foi o de par com escopo limitado: eu definia o que precisava, a IA propunha código ou explicações, e eu executava, testava e decidia aceitar, rejeitar ou adaptar.

---

## Sugestões aceitas

### 1. Funções de extração paginada (`buscar_pagina` e `extrair_tudo`)

Eu tinha escrito uma versão inicial que conectava com `https://` em vez de `http://`, e uma função `cria_brutos` com um bug (`dados` usada antes de ser atribuída). Após identificar o erro de conexão e descrever o que precisava — uma função que percorresse todas as páginas até `total_pages`, verificasse o status HTTP e tratasse erros de conexão e timeout com mensagem clara sem interromper o programa — a IA propôs a versão abaixo, que adotei:

```python
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
    total_paginas = 1

    while pagina <= total_paginas:
        dados = buscar_pagina(rota, pagina, tamanho)
        if dados is None:
            print(f"extracao: {rota} INCOMPLETA, falhou na pagina {pagina}")
            return None

        total_paginas = dados["total_pages"]
        registros.extend(dados["items"])
        pagina += 1

    rotulo = "registros_brutos" if rota == "pedidos" else "registros"
    print(f"extracao: {rota} paginas={total_paginas} {rotulo}={len(registros)}")
    return registros
```

**Por que aceitei:** o código trata os três cenários de erro (conexão, timeout, outros erros de rede) e retorna `None` em vez de deixar o programa quebrar com traceback. Também retorna `None` quando uma página falha no meio da extração, evitando carregar dados parciais. Validei testando com a API desligada (mensagem clara, sem traceback) e com uma página inexistente (mensagem de 404).

---

### 2. Arquivo `carga.py`

Pedi à IA que desenvolvesse o módulo de carga com base no `main.py` que eu já tinha e no `CONTRATO_DE_DADOS.md`. Os requisitos que defini: carregar na ordem correta das chaves estrangeiras (produtos, clientes, pedidos, itens_pedido), usar parâmetros em todas as inserções, garantir idempotência com `TRUNCATE ... CASCADE` dentro da mesma transação, e imprimir as linhas de reconciliação no formato do enunciado.

**Por que aceitei:** a estratégia de idempotência com `TRUNCATE` dentro de `with conn:` garante que ou tudo é carregado ou nada é, sem estado parcial. Os `%s` parametrizados nunca concatenam dados ao SQL. Rodei o ETL duas vezes seguidas e as contagens foram idênticas, confirmando a idempotência.

---

## Sugestões rejeitadas

### 1. Versão inicial das funções `tratar_email` e `padronizar_estado`

A IA propôs inicialmente:

```python
def tratar_email(cliente):
    email_cliente = cliente["email"]
    for email in email_cliente:   # itera sobre os caracteres da string
        if email is None:
            cliente["email"] = "Nulo"
    return cliente

def padronizar_estado(cliente):
    estado_cliente = cliente["estado"]
    for estado in estado_cliente:   # itera sobre os caracteres
        estado = estado.upper()     # atribuição local, não altera nada
    return cliente
```

**Por que rejeitei:** `for email in email_cliente` itera sobre os caracteres da string, não sobre o campo. Se o e-mail for `None`, o `for` levanta `TypeError` antes de chegar na comparação. Em `padronizar_estado`, `estado = estado.upper()` atribui a uma variável local e o cliente retorna sem nenhuma alteração. Nenhuma das duas funções fazia o que o nome prometia. Reescrevi usando `.get()` e atribuição direta ao dicionário.

---

### 2. `sys.exit(1)` dentro de `salvar_brutos`

Ao propor a função que combinava extração e salvamento, a IA incluiu `sys.exit(1)` diretamente dentro dela para encerrar o programa em caso de falha:

```python
def salvar_brutos(rota):
    registros = extrair_tudo(rota)
    if registros is None:
        sys.exit(1)   # encerra o programa aqui dentro
    os.makedirs("brutos", exist_ok=True)
    with open(f"brutos/{rota}.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
```

**Por que rejeitei:** `sys.exit` dentro de uma função auxiliar encerra o programa de um ponto escondido. Se essa função fosse importada num teste ou chamada de outro contexto, derrubaria tudo sem aviso. A IA mesma reconheceu o problema quando questionei: o correto é a função retornar `None` em caso de falha e deixar o `main` decidir se encerra. A versão final ficou com `salvar_brutos(rota, registros)` recebendo os dados como parâmetro, e o `sys.exit(1)` só no `main.py`.

---

## Falhas e retrabalho

### `marcar_divergencia` — erro de ponto flutuante na comparação de centavos

A IA propôs a seguinte comparação para detectar divergência:

```python
novo["divergente"] = abs(novo["valor_total"] - novo["valor_itens"]) > 0.01
```

Ao escrever o teste `test_a6_diferenca_de_um_centavo_nao_diverge`, que verifica que uma diferença de exatamente 1 centavo **não** é marcada como divergente, o pytest falhou:

```
FAILED tests/test_transformacao.py::test_a6_diferenca_de_um_centavo_nao_diverge - assert True is False
```

A causa: em ponto flutuante, `17.01 - 17.00` não é `0.01`, é `0.010000000000001563`, que é maior que `0.01`. A função marcava divergente quando não devia.

**Correção:** converter a diferença para centavos inteiros antes de comparar, eliminando o ruído de ponto flutuante:

```python
diferenca_centavos = round(abs(novo["valor_total"] - novo["valor_itens"]) * 100)
novo["divergente"] = diferenca_centavos > 1
```

Com isso, `0.010000000000001563 * 100` arredonda para `1`, e `1 > 1` é `False`, como a regra do enunciado exige. Todos os 30 testes passaram após a correção.
