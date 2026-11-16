import csv
import sys
from statistics import mean

from config import raiz
from speechPrep import prepararFala
from ttsModule import sintetizar

pastaTts = raiz / "testMaterial" / "tts"
avaliadores = ["avaliador1", "avaliador2", "avaliador3"]


def gerar():
    frases = [linha.strip() for linha in (pastaTts / "frases.txt").read_text(encoding="utf-8").splitlines() if linha.strip()]
    planilha = pastaTts / "avaliacao.csv"
    linhas = []
    for indice, frase in enumerate(frases, start=1):
        nome = f"tts{indice:02d}.mp3"
        sintetizar(prepararFala(frase), pastaTts / "audios" / nome)
        for avaliador in avaliadores:
            linhas.append({"arquivo": nome, "avaliador": avaliador, "naturalidade": "", "clareza": ""})
        print(f"gerado {nome}")
    if not planilha.exists():
        with open(planilha, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=["arquivo", "avaliador", "naturalidade", "clareza"])
            escritor.writeheader()
            escritor.writerows(linhas)
        print(f"planilha criada em {planilha}: peça a cada avaliador para ouvir os áudios e preencher notas de 1 a 5")


def resumir():
    with open(pastaTts / "avaliacao.csv", encoding="utf-8") as arquivo:
        linhas = [linha for linha in csv.DictReader(arquivo) if linha["naturalidade"] and linha["clareza"]]
    if not linhas:
        print("Planilha ainda sem notas.")
        return
    print(f"Naturalidade média: {mean(float(l['naturalidade']) for l in linhas):.2f}")
    print(f"Clareza média: {mean(float(l['clareza']) for l in linhas):.2f}")
    for avaliador in avaliadores:
        dele = [l for l in linhas if l["avaliador"] == avaliador]
        if dele:
            print(f"  {avaliador}: naturalidade {mean(float(l['naturalidade']) for l in dele):.2f}, clareza {mean(float(l['clareza']) for l in dele):.2f}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "resumo":
        resumir()
    else:
        gerar()


main()
