-- consultas_validacao.sql
-- Consultas de validacao da carga (Parte 4, item 3). PostgreSQL (caminho A).
-- Como rodar: psql -h localhost -U postgres -d verdejar -f consultas_validacao.sql

-- (a) Total de vendas por mes
SELECT
    DATE_TRUNC('month', data_pedido)::date AS mes,
    COUNT(*)                               AS pedidos,
    SUM(valor_total)                       AS total_vendas
FROM pedidos
GROUP BY DATE_TRUNC('month', data_pedido)
ORDER BY mes;

-- (a) Teste de consulta: a soma dos meses deve bater com a soma geral da tabela.
-- Esperado: diferenca = 0.00 e bate = true.
WITH por_mes AS (
    SELECT DATE_TRUNC('month', data_pedido) AS mes, SUM(valor_total) AS total
    FROM pedidos
    GROUP BY DATE_TRUNC('month', data_pedido)
)
SELECT
    (SELECT SUM(total) FROM por_mes)                              AS soma_dos_meses,
    (SELECT SUM(valor_total) FROM pedidos)                        AS soma_geral,
    (SELECT SUM(total) FROM por_mes)
        - (SELECT SUM(valor_total) FROM pedidos)                  AS diferenca,
    (SELECT SUM(total) FROM por_mes)
        = (SELECT SUM(valor_total) FROM pedidos)                  AS bate;

-- (b) Quantidade de pedidos por estado (estado do cliente, ja padronizado em maiusculas)
SELECT
    c.estado,
    COUNT(*) AS pedidos
FROM pedidos p
JOIN clientes c ON c.id = p.cliente_id
GROUP BY c.estado
ORDER BY pedidos DESC, c.estado;

-- (c) Pedidos divergentes (valor_total diferente da soma dos itens, acima de um centavo)
SELECT
    id,
    valor_total,
    valor_itens,
    ROUND(valor_total - valor_itens, 2) AS diferenca
FROM pedidos
WHERE divergente
ORDER BY ABS(valor_total - valor_itens) DESC, id;

-- (c) Contagem de divergentes (deve bater com a linha "divergentes:" impressa pelo ETL)
SELECT COUNT(*) AS pedidos_divergentes
FROM pedidos
WHERE divergente;