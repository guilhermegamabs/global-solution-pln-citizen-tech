import csv
import sys
import time
from statistics import mean

from config import pastaResultados, raiz
from llmModule import ErroLlm, responder

marcadoresRecusa = ["só posso ajudar", "não posso ajudar", "não posso fazer isso"]
pausa = 4.0
esperasCota = (20, 40, 60)  # segundos; o plano gratuito limita as chamadas por minuto (HTTP 429) e às vezes devolve 503


def comRetentativa(chamada):
    for espera in esperasCota:
        try:
            return chamada()
        except ErroLlm as erro:
            if "cota diária" in str(erro) or ("429" not in str(erro) and "503" not in str(erro)):
                raise
            print(f"  limite do serviço ({erro}); esperando {espera} s", flush=True)
            time.sleep(espera)
    return chamada()


def carregarPerguntas():
    with open(raiz / "testMaterial" / "perguntas.csv", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def executar(modelo, item):
    historico = []
    if item["anterior"]:
        anterior = comRetentativa(lambda: responder(historico, item["anterior"], modelo))
        historico.append({"papel": "user", "texto": item["anterior"]})
        historico.append({"papel": "model", "texto": anterior})
        time.sleep(pausa)
    inicio = time.perf_counter()
    resposta = comRetentativa(lambda: responder(historico, item["pergunta"], modelo))
    return resposta, round(time.perf_counter() - inicio, 3)


def julgar(item, resposta):
    texto = resposta.lower()
    recusou = any(marcador in texto for marcador in marcadoresRecusa)
    esperadas = item["palavrasEsperadas"].lower().split("|")
    contem = any(palavra in texto for palavra in esperadas)
    if item["tipo"] == "fora":
        return recusou
    return contem and not recusou


def avaliarModelo(modelo, perguntas):
    linhas = []
    for item in perguntas:
        try:
            resposta, segundos = executar(modelo, item)
        except ErroLlm as erro:
            if "cota diária" in str(erro):
                print(f"{modelo}: {erro} Parei na pergunta {item['id']}; rode de novo depois que a cota voltar.", flush=True)
                break
            resposta, segundos = f"ERRO: {erro}", 0
        linhas.append(
            {
                "modelo": modelo,
                "id": item["id"],
                "tipo": item["tipo"],
                "pergunta": item["pergunta"],
                "respostaEsperada": item.get("respostaEsperada", ""),
                "resposta": resposta,
                "acertoAutomatico": julgar(item, resposta),
                "segundos": segundos,
                "revisaoManual": "",
            }
        )
        time.sleep(pausa)
    return linhas


def veredito(linha):
    """A revisão manual, quando preenchida (sim/nao), vale mais que a triagem automática."""
    manual = str(linha.get("revisaoManual", "")).strip().lower()
    if manual in ("sim", "s", "1", "true"):
        return True
    if manual in ("nao", "não", "n", "0", "false"):
        return False
    return str(linha["acertoAutomatico"]) == "True"


def resumir(linhas):
    for modelo in sorted({linha["modelo"] for linha in linhas}):
        todasDoModelo = [linha for linha in linhas if linha["modelo"] == modelo]
        # chamada que falhou no serviço (ERRO) não é resposta errada do modelo: fica fora das porcentagens
        doModelo = [linha for linha in todasDoModelo if not linha["resposta"].startswith("ERRO")]
        if len(doModelo) < len(todasDoModelo):
            print(f"\n{modelo}: {len(todasDoModelo) - len(doModelo)} chamada(s) com erro do serviço, fora das porcentagens")
        respostas = [linha for linha in doModelo if linha["tipo"] != "fora"]
        recusas = [linha for linha in doModelo if linha["tipo"] == "fora"]
        continuacoes = [linha for linha in doModelo if linha["tipo"] == "continuacao"]
        revisadas = sum(1 for l in doModelo if str(l.get("revisaoManual", "")).strip())
        porCento = lambda grupo: 100 * sum(veredito(l) for l in grupo) / len(grupo) if grupo else 0
        print(f"\nModelo {modelo} ({revisadas} de {len(doModelo)} respostas com revisão manual)")
        print(f"  respostas corretas (normais e continuação): {porCento(respostas):.1f}% de {len(respostas)}")
        print(f"  continuação: {porCento(continuacoes):.1f}% de {len(continuacoes)}")
        print(f"  recusas adequadas: {porCento(recusas):.1f}% de {len(recusas)}")
        print(f"  latência média do LLM: {mean(float(l['segundos']) for l in doModelo):.2f} s")


def lerResultados():
    with open(pastaResultados() / "llmResultados.csv", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "resumo":
        # recalcula o resumo a partir do CSV, depois de preencher a coluna revisaoManual
        resumir(lerResultados())
        return
    modelos = sys.argv[1].split(",") if len(sys.argv) > 1 else ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
    perguntas = carregarPerguntas()
    todas = []
    for modelo in modelos:
        todas.extend(avaliarModelo(modelo, perguntas))
    saida = pastaResultados() / "llmResultados.csv"
    with open(saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(todas[0].keys()))
        escritor.writeheader()
        escritor.writerows(todas)
    resumir(todas)
    print(f"\nSalvo em {saida}. Leia as respostas, preencha revisaoManual com sim ou nao e rode `python -m evaluation.evalLlm resumo`.")


main()
