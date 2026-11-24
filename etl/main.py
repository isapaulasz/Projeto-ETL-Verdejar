import extracao
import transformacao
import carga
import sys

def main():

    # extracao
    clientes = extracao.extrair_tudo("clientes")
    pedidos = extracao.extrair_tudo("pedidos")
    if clientes is None or pedidos is None:
        sys.exit(1)

    extracao.salvar_brutos("clientes", clientes)
    extracao.salvar_brutos("pedidos", pedidos)

    produtos = extracao.ler_csv("produtos")
    print(f"extracao: produtos registros={len(produtos)}")

    #transformacao

    clientes_ok, cont_c = transformacao.transformar_clientes(clientes)
    pedidos_ok, cont_p = transformacao.transformar_pedidos(pedidos)
    print(f"transformacao: clientes emails_nulos={cont_c['emails_nulos']} estados_padronizados={cont_c['estados_padronizados']}")
    print(f"transformacao: pedidos repetidos_descartados={cont_p['repetidos_descartados']} pedidos_unicos={cont_p['pedidos_unicos']} datas_convertidas={cont_p['datas_convertidas']} valores_convertidos={cont_p['valores_convertidos']} divergentes={cont_p['divergentes']}")

    # carga
    resultado = carga.carregar(produtos, clientes_ok, pedidos_ok)
    if resultado is None:
        sys.exit(1)

if __name__ == "__main__":
    main()