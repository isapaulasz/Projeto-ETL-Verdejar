from etl.transformacao import (
    converter_data,
    converter_valor,
    remover_repetidos,
    tratar_email,
    padronizar_estado,
    marcar_divergencia,
    transformar_clientes,
)

# ---------- A3: conversão de data ----------

def test_data_dd_mm_aaaa():
    assert converter_data("25/11/2026") == "2026-11-25"

def test_data_iso_permanece():
    assert converter_data("2026-11-25") == "2026-11-25"


# ---------- A4: conversão de valor ----------

def test_valor_com_virgula():
    assert converter_valor("125,84") == 125.84


# ---------- A5: remoção de repetidos ----------

def test_repetidos_mantem_primeiro():
    pedidos = [{"id": 1, "x": "a"}, {"id": 1, "x": "a"}, {"id": 2, "x": "b"}]
    assert [p["id"] for p in remover_repetidos(pedidos)] == [1, 2]



# ---------- A1: e-mail ausente ----------

def test_a1_email_none_continua_nulo():
    cliente = {"id": 1, "email": None, "estado": "RS"}
    assert tratar_email(cliente)["email"] is None


def test_a1_email_vazio_vira_nulo():
    cliente = {"id": 1, "email": "  ", "estado": "RS"}
    assert tratar_email(cliente)["email"] is None


def test_a1_email_valido_permanece():
    cliente = {"id": 1, "email": "ana@exemplo.com", "estado": "RS"}
    assert tratar_email(cliente)["email"] == "ana@exemplo.com"


def test_a1_cliente_e_mantido_e_entrada_nao_e_alterada():
    cliente = {"id": 7, "email": None, "estado": "SP"}
    resultado = tratar_email(cliente)
    assert resultado["id"] == 7
    assert cliente["email"] is None  # original intacto


def test_a1_contador_de_emails_nulos():
    clientes = [
        {"id": 1, "email": None, "estado": "RS"},
        {"id": 2, "email": "b@x.com", "estado": "SP"},
        {"id": 3, "email": None, "estado": "PR"},
    ]
    _, contadores = transformar_clientes(clientes)
    assert contadores["emails_nulos"] == 2


# ---------- A2: sigla do estado ----------

def test_a2_minuscula_vira_maiuscula():
    cliente = {"id": 1, "email": "a@x.com", "estado": "rs"}
    assert padronizar_estado(cliente)["estado"] == "RS"


def test_a2_maiuscula_permanece():
    cliente = {"id": 1, "email": "a@x.com", "estado": "SP"}
    assert padronizar_estado(cliente)["estado"] == "SP"


def test_a2_entrada_nao_e_alterada():
    cliente = {"id": 1, "email": "a@x.com", "estado": "rs"}
    padronizar_estado(cliente)
    assert cliente["estado"] == "rs"


def test_a2_contador_conta_so_os_corrigidos():
    clientes = [
        {"id": 1, "email": "a@x.com", "estado": "rs"},
        {"id": 2, "email": "b@x.com", "estado": "SP"},
        {"id": 3, "email": "c@x.com", "estado": "pr"},
    ]
    resultado, contadores = transformar_clientes(clientes)
    assert [c["estado"] for c in resultado] == ["RS", "SP", "PR"]
    assert contadores["estados_padronizados"] == 2


# ---------- A6: divergência entre valor_total e soma dos itens ----------

def _pedido(valor_total, itens):
    return {"id": 1, "valor_total": valor_total, "itens": itens}


ITENS = [
    {"quantidade": 2, "preco_unitario": 3.50},
    {"quantidade": 1, "preco_unitario": 10.00},
]  # soma = 17.00


def test_a6_valor_itens_e_soma_de_quantidade_vezes_preco():
    resultado = marcar_divergencia(_pedido(17.00, ITENS))
    assert resultado["valor_itens"] == 17.00


def test_a6_totais_iguais_nao_diverge():
    assert marcar_divergencia(_pedido(17.00, ITENS))["divergente"] is False


def test_a6_totais_diferentes_diverge():
    resultado = marcar_divergencia(_pedido(20.00, ITENS))
    assert resultado["divergente"] is True
    assert resultado["valor_total"] == 20.00  # os dois valores são gravados
    assert resultado["valor_itens"] == 17.00


def test_a6_diferenca_de_um_centavo_nao_diverge():
    # a regra é "maior que um centavo": exatamente 0.01 não conta
    assert marcar_divergencia(_pedido(17.01, ITENS))["divergente"] is False


def test_a6_diferenca_de_dois_centavos_diverge():
    assert marcar_divergencia(_pedido(17.02, ITENS))["divergente"] is True


def test_a6_preco_unitario_em_texto_com_virgula():
    itens = [{"quantidade": 2, "preco_unitario": "3,50"}]
    assert marcar_divergencia(_pedido(7.00, itens))["valor_itens"] == 7.00