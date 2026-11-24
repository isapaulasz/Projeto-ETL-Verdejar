"""Testes do relatorio de qualidade (Stretch)."""
import csv
from datetime import datetime, timedelta, timezone

from etl.relatorio import COLUNAS, gerar_relatorio, gravar_relatorio, montar_linhas
from etl.transformacao import transformar_clientes, transformar_pedidos

DATA_HORA = "2026-11-24T21:00:00-03:00"
FUSO_BRASILIA = timezone(timedelta(hours=-3))

CONT_CLIENTES = {"emails_nulos": 81, "estados_padronizados": 151}
CONT_PEDIDOS = {
    "repetidos_descartados": 100,
    "pedidos_unicos": 5000,
    "datas_convertidas": 1037,
    "valores_convertidos": 1255,
    "divergentes": 238,
}


def _ler_csv(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- montagem das linhas (funcao pura) ----------

def test_seis_linhas_uma_por_armadilha_na_ordem():
    linhas = montar_linhas(DATA_HORA, CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100)
    assert [l["armadilha"] for l in linhas] == ["A1", "A2", "A3", "A4", "A5", "A6"]


def test_contador_de_cada_armadilha_vem_da_fonte_certa():
    linhas = montar_linhas(DATA_HORA, CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100)
    contadores = {l["armadilha"]: l["contador"] for l in linhas}
    assert contadores == {"A1": 81, "A2": 151, "A3": 1037, "A4": 1255, "A5": 100, "A6": 238}


def test_total_avaliado_usa_a_base_de_cada_armadilha():
    linhas = montar_linhas(DATA_HORA, CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100)
    totais = {l["armadilha"]: l["total_avaliado"] for l in linhas}
    # A1 e A2 sobre clientes; A5 sobre pedidos brutos; A3, A4 e A6 sobre pedidos unicos
    assert totais == {"A1": 1000, "A2": 1000, "A3": 5000, "A4": 5000, "A5": 5100, "A6": 5000}


def test_data_hora_e_a_mesma_nas_seis_linhas():
    linhas = montar_linhas(DATA_HORA, CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100)
    assert {l["data_hora"] for l in linhas} == {DATA_HORA}


# ---------- gravacao do arquivo ----------

def test_cria_pasta_arquivo_e_cabecalho(tmp_path):
    caminho = tmp_path / "relatorios" / "relatorio_qualidade.csv"
    linhas = montar_linhas(DATA_HORA, CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100)
    gravar_relatorio(linhas, str(caminho))

    with open(caminho, encoding="utf-8") as f:
        assert f.readline().strip().split(",") == COLUNAS
    assert len(_ler_csv(caminho)) == 6


def test_duas_execucoes_acumulam_sem_repetir_cabecalho(tmp_path):
    caminho = str(tmp_path / "relatorio_qualidade.csv")
    primeira = datetime(2026, 11, 24, 21, 0, 0, tzinfo=FUSO_BRASILIA)
    segunda = datetime(2026, 11, 24, 21, 5, 0, tzinfo=FUSO_BRASILIA)

    gerar_relatorio(CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100, caminho, agora=primeira)
    gerar_relatorio(CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100, caminho, agora=segunda)

    linhas = _ler_csv(caminho)
    assert len(linhas) == 12  # 6 por execucao
    assert {l["data_hora"] for l in linhas} == {
        "2026-11-24T21:00:00-03:00",
        "2026-11-24T21:05:00-03:00",
    }
    with open(caminho, encoding="utf-8") as f:
        assert f.read().count("data_hora") == 1  # so uma linha de cabecalho


def test_data_hora_gravada_e_iso_8601_com_fuso(tmp_path):
    caminho = str(tmp_path / "relatorio_qualidade.csv")
    agora = datetime(2026, 11, 25, 9, 30, 15, tzinfo=FUSO_BRASILIA)
    gerar_relatorio(CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100, caminho, agora=agora)

    data_hora = _ler_csv(caminho)[0]["data_hora"]
    assert data_hora == "2026-11-25T09:30:15-03:00"
    assert datetime.fromisoformat(data_hora) == agora  # volta a ser a mesma data e hora


def test_sem_agora_usa_a_hora_atual_com_fuso(tmp_path):
    caminho = str(tmp_path / "relatorio_qualidade.csv")
    gerar_relatorio(CONT_CLIENTES, CONT_PEDIDOS, 1000, 5100, caminho)

    data_hora = datetime.fromisoformat(_ler_csv(caminho)[0]["data_hora"])
    assert data_hora.tzinfo is not None


# ---------- integracao: contadores reais da transformacao ----------

def test_relatorio_com_contadores_vindos_da_transformacao(tmp_path):
    clientes = [
        {"id": 1, "email": None, "estado": "rs"},
        {"id": 2, "email": "b@x.com", "estado": "SP"},
        {"id": 3, "email": "", "estado": "pr"},
    ]
    itens = [{"quantidade": 2, "preco_unitario": 5.00}]  # soma = 10.00
    pedidos = [
        {"id": 1, "data_pedido": "2026-01-10", "valor_total": 10.00, "itens": itens},
        {"id": 2, "data_pedido": "15/02/2026", "valor_total": "10,00", "itens": itens},
        {"id": 2, "data_pedido": "15/02/2026", "valor_total": "10,00", "itens": itens},  # repetido
        {"id": 3, "data_pedido": "2026-03-20", "valor_total": 99.00, "itens": itens},  # divergente
    ]
    _, cont_c = transformar_clientes(clientes)
    _, cont_p = transformar_pedidos(pedidos)

    caminho = str(tmp_path / "relatorio_qualidade.csv")
    gerar_relatorio(cont_c, cont_p, len(clientes), len(pedidos), caminho)

    por_armadilha = {l["armadilha"]: l for l in _ler_csv(caminho)}
    assert por_armadilha["A1"]["contador"] == "2"  # None e "" contam como e-mail ausente
    assert por_armadilha["A2"]["contador"] == "2"  # rs e pr corrigidos
    assert por_armadilha["A3"]["contador"] == "1"  # so 15/02/2026 precisou converter
    assert por_armadilha["A4"]["contador"] == "1"  # so "10,00" era texto
    assert por_armadilha["A5"]["contador"] == "1"  # um pedido repetido
    assert por_armadilha["A6"]["contador"] == "1"  # so o pedido 3 diverge
    assert por_armadilha["A5"]["total_avaliado"] == "4"  # 4 pedidos brutos
    assert por_armadilha["A3"]["total_avaliado"] == "3"  # 3 pedidos unicos
