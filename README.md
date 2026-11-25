# Projeto-ETL-Verdejar

Projeto desenvolvido durante o Bootcamp AI-Driven Data Engineering (Fellowship OCT26) da AI/R.

O ETL extrai clientes e pedidos de uma API HTTP local paginada e os produtos de um CSV, trata seis problemas de qualidade conhecidos nos dados (armadilhas A1 a A6), carrega tudo em um banco PostgreSQL e imprime uma reconciliação entre origem e destino. Os dados são sintéticos (seed 2026).

---

## Estrutura

| Caminho | Função |
|---|---|
| `etl/extracao.py` | Lê as rotas `/clientes` e `/pedidos` da API, página por página, e o `produtos.csv`. Salva os dados brutos em `brutos/`. |
| `etl/transformacao.py` | Trata as armadilhas A1 a A6 e devolve os contadores de cada uma. |
| `etl/carga.py` | Carrega no PostgreSQL em uma única transação e imprime a reconciliação. |
| `etl/relatorio.py` | Relatório de qualidade (Stretch): grava os contadores de cada execução em CSV. |
| `etl/main.py` | Orquestra extração, transformação, relatório e carga. |
| `tests/` | Testes de transformação, de reconciliação e do relatório. |
| `consultas_validacao.sql` | Consultas de validação da carga. |
| `CONTRATO_DE_DADOS.md` | Campos, tipos, nulidade e regra de transformação de cada tabela. |
| `insumos/` | Material fornecido pelo desafio: API local, dados, gerador e esquemas SQL. |

---

## Pré-requisitos

- Python 3
- PostgreSQL instalado e em execução (caminho A do desafio), com um banco chamado `verdejar`

### Instalar dependências

```
pip install requests "psycopg[binary]" pytest
```

Usar um ambiente virtual é opcional, mas recomendado para não misturar dependências com outros projetos:

```
python -m venv .venv && source .venv/bin/activate
```

---

## Configuração do banco

1. Crie o banco e aplique o esquema:

   ```
   createdb -h localhost -U postgres verdejar
   psql -h localhost -U postgres -d verdejar -f insumos/schema.sql
   ```

2. Crie um arquivo `.env` na raiz do projeto (ele está no `.gitignore` e não vai para o repositório):

   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=verdejar
   DB_USER=postgres
   DB_PASSWORD=sua_senha
   ```

   O código também aceita os nomes `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` e `PGPASSWORD`. Variáveis já definidas no ambiente têm prioridade sobre o `.env`. Sem nenhuma configuração, usa `localhost`, porta `5432`, banco `verdejar` e usuário `postgres`.

---

## Como rodar

Execute tudo a partir da **raiz do projeto**, porque os caminhos `insumos/dados/` e `brutos/` são relativos.

1. Suba a API em um terminal:

   ```
   python insumos/api_verdejar.py
   ```

   Ela fica em `http://127.0.0.1:8000`. Para conferir: `curl http://127.0.0.1:8000/saude`.

2. Em outro terminal, rode o ETL:

   ```
   python -m etl.main
   ```

3. Rode os testes (depois do ETL, porque o teste de reconciliação lê `brutos/pedidos.json` e o banco):

   ```
   python -m pytest
   ```

   Se o ETL não tiver rodado ou o banco estiver fora do ar, os dois testes de reconciliação são ignorados (skip) em vez de falharem.

### Saída do ETL (seed 2026)

```
extracao: clientes paginas=10 registros=1000
extracao: pedidos paginas=51 registros_brutos=5100
extracao: produtos registros=12
transformacao: clientes emails_nulos=81 estados_padronizados=151
transformacao: pedidos repetidos_descartados=100 pedidos_unicos=5000 datas_convertidas=1037 valores_convertidos=1255 divergentes=238
relatorio: arquivo=relatorios/relatorio_qualidade.csv data_hora=... armadilhas=6
carga: clientes=1000 produtos=12 pedidos=5000 itens=12455
reconciliacao: soma_valor_itens_origem=311228.75 soma_valor_itens_destino=311228.75 diferenca=0.00
divergentes: 238 pedidos com valor_total diferente da soma dos itens
```

### Resultado dos testes

```
30 passed in 0.35s
```

---

## Tratamento das armadilhas

| Armadilha | Problema nos dados | Tratamento | Ocorrências |
|---|---|---|---|
| A1 | E-mail ausente (nulo ou vazio) | Cliente mantido, e-mail gravado como `NULL` | 81 |
| A2 | Sigla do estado em caixa mista | Remove espaços e converte para maiúsculas | 151 |
| A3 | Datas em `AAAA-MM-DD` e `DD/MM/AAAA` | Converte tudo para `AAAA-MM-DD` | 1037 |
| A4 | `valor_total` como texto com vírgula (`125,84`) | Converte para número com 2 casas decimais | 1255 |
| A5 | Pedidos repetidos entre páginas | Mantém a primeira ocorrência de cada `id` | 100 |
| A6 | `valor_total` diferente da soma dos itens | Calcula `valor_itens` e marca `divergente` quando a diferença passa de 1 centavo | 238 |

Os pedidos divergentes **não são corrigidos nem descartados**: os dois valores são gravados e o pedido fica marcado com `divergente = true`. Os detalhes de cada campo estão em `CONTRATO_DE_DADOS.md`.

Os contadores de A3, A4 e A6 são calculados sobre os 5000 pedidos únicos, já sem os repetidos. O de A5 sai dos 5100 pedidos brutos.

---

## Idempotência

A carga começa com `TRUNCATE itens_pedido, pedidos, clientes, produtos CASCADE` e insere os dados na **mesma transação**. Rodar o ETL várias vezes deixa o banco sempre com o mesmo conteúdo, sem duplicar linhas. Se qualquer inserção falhar, o rollback restaura o estado anterior do banco. Todas as inserções usam parâmetros, nunca SQL montado com concatenação de dados.

Isso foi conferido rodando o ETL duas vezes seguidas: as contagens e a reconciliação saíram idênticas nas duas execuções.

---

## Reconciliação e testes

**Reconciliação.** Ao final da carga, o ETL compara a soma de `valor_itens` calculada na origem com a soma lida do banco (`diferenca=0.00` na execução acima) e imprime a contagem de pedidos divergentes no banco, que coincide com o contador de A6.

**Testes** (`python -m pytest`, 30 testes com o ETL já executado):

- `tests/test_transformacao.py`: A1 e A2 (incluindo os contadores), conversão de data (A3), de valor (A4), remoção de repetidos (A5) e a regra de divergência de A6, com os casos de 1 e 2 centavos de diferença.
- `tests/test_reconciliacao.py`: compara a **contagem de pedidos únicos** e a **soma de `valor_itens`** entre `brutos/pedidos.json` e a tabela `pedidos` (tolerância de 1 centavo). A origem é recalculada no próprio teste, sem reutilizar as funções do ETL, para o teste não concordar com um erro do código.
- `tests/test_relatorio.py`: ver a seção do relatório de qualidade abaixo.

---

## Consultas de validação

`consultas_validacao.sql` reúne consultas para conferir a carga:

```
psql -h localhost -U postgres -d verdejar -f consultas_validacao.sql
```

- **(a)** Total de vendas por mês, com uma consulta de teste que compara a soma dos meses com a soma geral da tabela.

``` 
    mes     | pedidos | total_vendas 
------------+---------+--------------
 2026-01-01 |     488 |     30449.02
 2026-02-01 |     536 |     33923.86
 2026-03-01 |     487 |     30678.70
 2026-04-01 |     521 |     31253.96
 2026-05-01 |     512 |     30890.02
 2026-06-01 |     523 |     31627.73
 2026-07-01 |     519 |     32796.17
 2026-08-01 |     458 |     29328.04
 2026-09-01 |     476 |     29995.71
 2026-10-01 |     480 |     31104.54
```

- **(b)** Quantidade de pedidos por estado do cliente.

```
 soma_dos_meses | soma_geral | diferenca | bate 
----------------+------------+-----------+------
      312047.75 |  312047.75 |      0.00 | t
```

- **(c)** Lista de pedidos divergentes e a contagem deles, que deve bater com a linha `divergentes:` impressa pelo ETL.

```
 estado | pedidos 
--------+---------
 RS     |    1543
 SC     |    1127
 PR     |     974
 SP     |     880
 MG     |     476
```

---

## Stretch: relatório de qualidade

A cada execução, o ETL acrescenta ao arquivo `relatorios/relatorio_qualidade.csv` os contadores das seis armadilhas, com a data e a hora da execução. O código está em `etl/relatorio.py` e é chamado pelo `etl/main.py` logo depois da transformação. Para gerar, basta rodar o ETL: a pasta e o arquivo são criados na primeira execução.

| Coluna | Significado |
|---|---|
| `data_hora` | Data e hora da execução (ISO 8601, com fuso). É igual nas seis linhas da mesma execução. |
| `armadilha` | Código A1 a A6. |
| `descricao` | O que o ETL tratou. |
| `contador` | Quantos registros foram tratados. |
| `total_avaliado` | Quantos registros foram examinados, para dar proporção ao contador. |

Resultado com a seed 2026 (os números são os mesmos em toda execução, porque os dados são fixos):

| Armadilha | Contador | Total avaliado |
|---|---|---|
| A1 | 81 | 1000 clientes |
| A2 | 151 | 1000 clientes |
| A3 | 1037 | 5000 pedidos únicos |
| A4 | 1255 | 5000 pedidos únicos |
| A5 | 100 | 5100 pedidos brutos |
| A6 | 238 | 5000 pedidos únicos |

Decisões:

- O arquivo **acumula**: cada execução acrescenta 6 linhas e nada é apagado, então o histórico mostra a qualidade dos dados ao longo do tempo. Isso não afeta a idempotência do banco, que é garantida pela carga.
- O relatório é gravado **antes da carga**, porque descreve a qualidade dos dados de origem. Se o banco estiver fora do ar, a execução ainda deixa o seu registro.
- Os contadores vêm das funções de transformação já existentes; o módulo do relatório não recalcula nada.
- Os valores foram conferidos de forma independente, contando direto nos dados brutos sem usar as funções do ETL, e os números coincidem.

`tests/test_relatorio.py` cobre a montagem das seis linhas, a base de `total_avaliado` de cada armadilha, a criação do arquivo com cabeçalho, o acúmulo de duas execuções sem repetir o cabeçalho, o formato da data e hora, e um teste de integração com contadores reais da transformação.
