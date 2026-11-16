import csv
import time
from contextlib import contextmanager
from datetime import datetime

from config import pastaLogs

etapas = ["stt", "llm", "prep", "tts"]


@contextmanager
def medir(registro, etapa):
    inicio = time.perf_counter()
    try:
        yield
    finally:
        registro[etapa] = round(time.perf_counter() - inicio, 3)


def fechar(registro):
    registro["total"] = round(sum(registro.get(etapa, 0) for etapa in etapas), 3)
    return registro


def gravarCsv(registro, origem="app"):
    caminho = pastaLogs() / "latencia.csv"
    novo = not caminho.exists()
    with open(caminho, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(["data", "origem"] + etapas + ["total"])
        escritor.writerow(
            [datetime.now().isoformat(timespec="seconds"), origem]
            + [registro.get(etapa, 0) for etapa in etapas]
            + [registro["total"]]
        )
