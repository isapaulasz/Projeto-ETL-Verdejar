from datetime import datetime

# A1
def tratar_email(cliente):  
    novo = dict(cliente)
    email = novo.get("email")
    if email is None or str(email).strip() == "":
        novo["email"] = None
    return novo

# A2
def padronizar_estado(cliente):  
    novo = dict(cliente)
    estado = novo.get("estado")
    if estado is not None:
        novo["estado"] = estado.strip().upper()
    return novo

# A3
def converter_data(texto):  
    texto = texto.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Formato de data desconhecido: {texto!r}")

# A4
def converter_valor(valor):  
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
    return round(float(valor), 2)

# A5
def remover_repetidos(pedidos):  
    vistos = set()
    unicos = []
    for p in pedidos:
        if p["id"] not in vistos:
            vistos.add(p["id"])
            unicos.append(p)
    return unicos


# A6
def marcar_divergencia(pedido):  
    novo = dict(pedido)
    novo["valor_itens"] = round(
        sum(i["quantidade"] * converter_valor(i["preco_unitario"]) for i in novo["itens"]), 2
    )
    novo["divergente"] = abs(novo["valor_total"] - novo["valor_itens"]) > 0.01
    return novo


def transformar_clientes(clientes):
    contadores = {"emails_nulos": 0, "estados_padronizados": 0}
    resultado = []
    for c in clientes:
        if c.get("email") is None or str(c["email"]).strip() == "":
            contadores["emails_nulos"] += 1
        novo = tratar_email(c)
        novo2 = padronizar_estado(novo)
        if novo2["estado"] != c.get("estado"):
            contadores["estados_padronizados"] += 1
        resultado.append(novo2)
    return resultado, contadores


def transformar_pedidos(pedidos):
    contadores = {
        "repetidos_descartados": 0,
        "pedidos_unicos": 0,
        "datas_convertidas": 0,
        "valores_convertidos": 0,
        "divergentes": 0,
    }
    unicos = remover_repetidos(pedidos)
    contadores["repetidos_descartados"] = len(pedidos) - len(unicos)
    contadores["pedidos_unicos"] = len(unicos)

    resultado = []
    for p in unicos:
        novo = dict(p)
        data_nova = converter_data(novo["data_pedido"])
        if data_nova != novo["data_pedido"]:
            contadores["datas_convertidas"] += 1
        novo["data_pedido"] = data_nova

        if isinstance(novo["valor_total"], str):
            contadores["valores_convertidos"] += 1
        novo["valor_total"] = converter_valor(novo["valor_total"])

        novo = marcar_divergencia(novo)
        if novo["divergente"]:
            contadores["divergentes"] += 1
        resultado.append(novo)
    return resultado, contadores