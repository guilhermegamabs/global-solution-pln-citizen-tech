import csv
import json
import time
from statistics import mean

from config import pastaResultados, raiz
from latency import etapas
from pipeline import processarAudio
from llmModule import ErroLlm
from ttsModule import sintetizar

pausa = 1.0


def carregarConversas():
    return json.loads((raiz / "testMaterial" / "conversas.json").read_text(encoding="utf-8"))


def obterAudio(turno):
    if turno.get("audio"):
        return str(raiz / "testMaterial" / turno["audio"]), "gravado"
    return sintetizar(turno["texto"]), "sintetico"


def executarConversa(conversa):
    historico = []
    linhas = []
    for numero, turno in enumerate(conversa["turnos"], start=1):
        caminho, origem = obterAudio(turno)
        try:
            resultado = processarAudio(caminho, historico, apagarAudio=origem == "sintetico", origem="e2e")
        except ErroLlm as erro:
            print(f"erro em {conversa['id']} turno {numero}: {erro}")
            continue
        if resultado is None:
            continue
        linha = {"conversa": conversa["id"], "turno": numero, "origemAudio": origem, "transcricao": resultado["texto"], "resposta": resultado["resposta"]}
        for etapa in etapas + ["total"]:
            linha[etapa] = resultado["latencia"].get(etapa, 0)
        linhas.append(linha)
        time.sleep(pausa)
    return linhas


def main():
    todas = []
    for conversa in carregarConversas():
        todas.extend(executarConversa(conversa))
        print(f"concluída {conversa['id']}")
    saida = pastaResultados() / "e2eResultados.csv"
    with open(saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(todas[0].keys()))
        escritor.writeheader()
        escritor.writerows(todas)
    print(f"\nLatência média em segundos ({len(todas)} turnos):")
    for etapa in etapas + ["total"]:
        print(f"  {etapa}: {mean(linha[etapa] for linha in todas):.2f}")
    print(f"Salvo em {saida}")


main()
