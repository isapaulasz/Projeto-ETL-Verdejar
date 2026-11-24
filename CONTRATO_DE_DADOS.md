# Contrato de dados

Contrato informal do ETL da Verdejar: o que cada campo recebe e entrega. As tabelas estão na ordem de carga (produtos, clientes, pedidos, itens_pedido), respeitando as chaves estrangeiras.

Legenda: "Admite nulo" indica se o campo pode ficar vazio no banco. Armadilhas A1 a A6 referem-se ao enunciado do desafio.

## produtos (origem: dados/produtos.csv)

| Campo | Tipo | Admite nulo | Regra de transformação |
| ----- | ---- | ----------- | ---------------------- |
| produto_id | inteiro | Não | Chave primária. Sem transformação. |
| nome | texto | Não | Sem transformação. |
| categoria | texto | Não | Sem transformação. |
| preco_base | numérico (2 casas) | Não | Converter para número com duas casas decimais. |

## clientes (origem: API /clientes)

| Campo | Tipo | Admite nulo | Regra de transformação |
| ----- | ---- | ----------- | ---------------------- |
| id | inteiro | Não | Chave primária. Sem transformação. |
| nome | texto | Não | Sem transformação. |
| email | texto | Sim | A1: quando ausente (nulo ou vazio), manter o cliente, gravar o e-mail como nulo e contar quantos são. |
| cidade | texto | Não | Sem transformação. |
| estado | texto de 2 letras | Não | A2: remover espaços e padronizar para maiúsculas (rs vira RS) antes da carga. |
| cadastro_em | data (DATE) | Não | Carregar como data no formato AAAA-MM-DD. |

## pedidos (origem: API /pedidos)

| Campo | Tipo | Admite nulo | Regra de transformação |
| ----- | ---- | ----------- | ---------------------- |
| id | inteiro | Não | Chave primária. A5: pedidos repetidos em páginas diferentes são carregados uma única vez, mantendo a primeira ocorrência. |
| cliente_id | inteiro | Não | Chave estrangeira para clientes.id. |
| data_pedido | data (DATE) | Não | A3: aceitar AAAA-MM-DD e DD/MM/AAAA e converter para AAAA-MM-DD (DATE no PostgreSQL). |
| status | texto | Não | Sem transformação. |
| valor_total | numérico (2 casas) | Não | A4: se vier como texto com vírgula decimal (125,84), converter para número com duas casas decimais. |
| valor_itens | numérico (2 casas) | Não | A6: calculado como a soma de quantidade vezes preco_unitario dos itens do pedido. |
| divergente | booleano | Não | A6: verdadeiro quando a diferença absoluta entre valor_total e valor_itens é maior que um centavo (0,01); caso contrário, falso. Contar quantos são. |

## itens_pedido (origem: itens aninhados em cada pedido da API)

| Campo | Tipo | Admite nulo | Regra de transformação |
| ----- | ---- | ----------- | ---------------------- |
| pedidos_id | inteiro | Não | Parte da chave primária. Chave estrangeira para pedidos.id. |
| linha | inteiro | Não | Parte da chave primária. Posição do item dentro do pedido. |
| produto_id | inteiro | Não | Chave estrangeira para produtos.produto_id. |
| quantidade | inteiro | Não | Sem transformação. |
| preco_unitario | numérico (2 casas) | Não | Converter para número com duas casas decimais, caso venha como texto com vírgula. |