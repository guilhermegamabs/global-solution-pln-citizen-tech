import csv
import sys
import time
from collections import defaultdict
from statistics import mean

import jiwer

from config import pastaResultados, raiz
from sttModule import transcrever
from textoAvaliacao import normalizar

pastaStt = raiz / "testMaterial" / "stt"

# Campos do roteiro usados na análise de viés. Os que o grupo não preencher são ignorados.
camposAnalise = ["voz", "ruido", "sexo", "faixaEtaria", "sotaque", "dispositivo"]


def carregarRoteiro():
    with open(pastaStt / "roteiro.csv", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def avaliarModelo(tamanho, roteiro):
    existentes = [item for item in roteiro if (pastaStt / "audios" / item["arquivo"]).exists()]
    for item in roteiro:
        if item not in existentes:
            print(f"ausente: {pastaStt / 'audios' / item['arquivo']}")
    if not existentes:
        return []
    # a primeira chamada carrega o modelo; sem este aquecimento ela entraria na latência média
    transcrever(pastaStt / "audios" / existentes[0]["arquivo"], tamanho)
    linhas = []
    for item in existentes:
        caminho = pastaStt / "audios" / item["arquivo"]
        inicio = time.perf_counter()
        hipotese = normalizar(transcrever(caminho, tamanho))
        segundos = round(time.perf_counter() - inicio, 3)
        referencia = normalizar(item["textoReferencia"])
        linha = {
            "modelo": tamanho,
            "arquivo": item["arquivo"],
            "referencia": referencia,
            "hipotese": hipotese,
            "wer": round(jiwer.wer(referencia, hipotese), 4),
            "segundos": segundos,
        }
        for campo in camposAnalise:
            linha[campo] = item.get(campo, "")
        linhas.append(linha)
    return linhas


def resumir(linhas):
    for modelo in sorted({linha["modelo"] for linha in linhas}):
        doModelo = [linha for linha in linhas if linha["modelo"] == modelo]
        print(f"\nModelo {modelo}: WER médio {mean(l['wer'] for l in doModelo):.3f} e "
              f"{mean(l['segundos'] for l in doModelo):.2f} s por áudio, em {len(doModelo)} áudios")
        for campo in camposAnalise:
            grupos = defaultdict(list)
            for linha in doModelo:
                if linha[campo]:
                    grupos[linha[campo]].append(linha["wer"])
            for grupo, valores in sorted(grupos.items()):
                print(f"  {campo}={grupo}: {mean(valores):.3f} ({len(valores)} áudios)")


def main():
    tamanhos = sys.argv[1].split(",") if len(sys.argv) > 1 else ["small", "medium"]
    roteiro = carregarRoteiro()
    todas = []
    for tamanho in tamanhos:
        todas.extend(avaliarModelo(tamanho, roteiro))
    if not todas:
        print("Nenhum áudio encontrado em testMaterial/stt/audios.")
        return
    saida = pastaResultados() / "sttResultados.csv"
    with open(saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(todas[0].keys()))
        escritor.writeheader()
        escritor.writerows(todas)
    resumir(todas)
    print(f"\nSalvo em {saida}")


main()
