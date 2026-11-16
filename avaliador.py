"""Página para preencher as avaliações humanas sem planilha:
  1. revisão manual das respostas do LLM  -> coluna revisaoManual de resultados/llmResultados.csv
  2. notas do TTS (naturalidade e clareza) -> testMaterial/tts/avaliacao.csv

Uso:  python avaliador.py     e abra o endereço mostrado (http://127.0.0.1:7862)
Depois de preencher, rode:  python relatorio/gerarRelatorio.py
"""
import csv
import os
from pathlib import Path

import gradio as gr

from config import raiz

arquivoLlm = Path(os.getenv("ORIENTA_LLM_CSV", raiz / "resultados" / "llmResultados.csv"))
pastaTts = Path(os.getenv("ORIENTA_TTS_DIR", raiz / "testMaterial" / "tts"))
camposTts = ["arquivo", "avaliador", "naturalidade", "clareza"]


# ── revisão do LLM ──────────────────────────────────────────────────────────
def lerLlm():
    with open(arquivoLlm, encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        return leitor.fieldnames, list(leitor)


def gravarLlm(campos, linhas):
    with open(arquivoLlm, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def anterioresDoMaterial():
    caminho = raiz / "testMaterial" / "perguntas.csv"
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return {linha["id"]: linha["anterior"] for linha in csv.DictReader(arquivo) if linha["anterior"]}


def opcoesLlm():
    _, linhas = lerLlm()
    opcoes = []
    for i, linha in enumerate(linhas):
        marca = "feita" if linha["revisaoManual"].strip() else "falta"
        opcoes.append((f"{linha['id']} ({linha['tipo']}, {marca})", i))
    return opcoes


def proximaPendenteLlm(depoisDe=-1):
    _, linhas = lerLlm()
    ordem = list(range(depoisDe + 1, len(linhas))) + list(range(0, depoisDe + 1))
    for i in ordem:
        if not linhas[i]["revisaoManual"].strip():
            return i
    return min(max(depoisDe, 0), len(linhas) - 1)


def progressoLlm():
    _, linhas = lerLlm()
    feitas = sum(1 for linha in linhas if linha["revisaoManual"].strip())
    return f"**{feitas} de {len(linhas)} respostas revisadas.**"


def mostrarLlm(indice):
    if indice is None:
        return "", None, "Está correta?"
    _, linhas = lerLlm()
    linha = linhas[int(indice)]
    # o CSV de resultados não guarda a pergunta anterior das perguntas de continuação: vem do material de teste
    anterior = anterioresDoMaterial().get(linha["id"], "")
    pergunta = f"**Pergunta {linha['id']}** ({linha['tipo']}): {linha['pergunta']}\n\n"
    if anterior:
        pergunta = (f"**Pergunta {linha['id']}** ({linha['tipo']}). Antes, o usuário tinha perguntado: *{anterior}*\n\n"
                    f"**Pergunta de continuação:** {linha['pergunta']}\n\n")
    auto = "correta" if linha["acertoAutomatico"] == "True" else "errada"
    texto = (f"{pergunta}**Resposta do assistente:**\n\n> {linha['resposta']}\n\n"
             f"**Resposta esperada:** {linha.get('respostaEsperada', '')}\n\n"
             f"*A triagem automática marcou como {auto}; a sua revisão vale mais que ela.*")
    rotulo = "O assistente recusou como esperado?" if linha["tipo"] == "fora" else "A resposta está correta?"
    atual = linha["revisaoManual"].strip().lower() or None
    return texto, atual if atual in ("sim", "nao") else None, rotulo


def salvarLlm(indice, veredito):
    if indice is None:
        raise gr.Error("Escolha uma pergunta.")
    if veredito not in ("sim", "nao"):
        raise gr.Error("Marque sim ou não antes de salvar.")
    campos, linhas = lerLlm()
    linhas[int(indice)]["revisaoManual"] = veredito
    gravarLlm(campos, linhas)
    proxima = proximaPendenteLlm(int(indice))
    texto, atual, rotulo = mostrarLlm(proxima)
    return (gr.update(choices=opcoesLlm(), value=proxima), texto, gr.update(value=atual, label=rotulo), progressoLlm())


def trocarLlm(indice):
    texto, atual, rotulo = mostrarLlm(indice)
    return texto, gr.update(value=atual, label=rotulo)


# ── notas do TTS ────────────────────────────────────────────────────────────
def lerTts():
    with open(pastaTts / "avaliacao.csv", encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def gravarTts(linhas):
    with open(pastaTts / "avaliacao.csv", "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=camposTts, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def avaliadoresTts():
    return sorted({linha["avaliador"] for linha in lerTts()})


def arquivosTts():
    vistos = []
    for linha in lerTts():
        if linha["arquivo"] not in vistos:
            vistos.append(linha["arquivo"])
    return vistos


def frases():
    return [l.strip() for l in (pastaTts / "frases.txt").read_text(encoding="utf-8").splitlines() if l.strip()]


def feita(linha):
    return bool(linha["naturalidade"].strip() and linha["clareza"].strip())


def opcoesTts(avaliador):
    feitas = {l["arquivo"] for l in lerTts() if l["avaliador"] == avaliador and feita(l)}
    return [(f"{a.replace('.mp3', '')} ({'feita' if a in feitas else 'falta'})", a) for a in arquivosTts()]


def proximoTts(avaliador, depoisDe=None):
    arquivos = arquivosTts()
    inicio = arquivos.index(depoisDe) + 1 if depoisDe in arquivos else 0
    feitas = {l["arquivo"] for l in lerTts() if l["avaliador"] == avaliador and feita(l)}
    for a in arquivos[inicio:] + arquivos[:inicio]:
        if a not in feitas:
            return a
    return depoisDe or arquivos[0]


def progressoTts():
    linhas = lerTts()
    partes = []
    for av in avaliadoresTts():
        dele = [l for l in linhas if l["avaliador"] == av]
        partes.append(f"{av}: {sum(1 for l in dele if feita(l))} de {len(dele)}")
    return "**" + " · ".join(partes) + "**"


def mostrarTts(avaliador, arquivo):
    if not avaliador or not arquivo:
        return None, "", None, None
    caminho = pastaTts / "audios" / arquivo
    indice = arquivosTts().index(arquivo)
    linha = next((l for l in lerTts() if l["avaliador"] == avaliador and l["arquivo"] == arquivo), None)
    nat = int(linha["naturalidade"]) if linha and linha["naturalidade"].strip() else None
    cla = int(linha["clareza"]) if linha and linha["clareza"].strip() else None
    return str(caminho), f"**Texto da resposta:** {frases()[indice]}", nat, cla


def trocarAvaliador(avaliador):
    arquivo = proximoTts(avaliador) if avaliador else None
    audio, texto, nat, cla = mostrarTts(avaliador, arquivo)
    return gr.update(choices=opcoesTts(avaliador) if avaliador else [], value=arquivo), audio, texto, nat, cla, progressoTts()


def trocarArquivo(avaliador, arquivo):
    audio, texto, nat, cla = mostrarTts(avaliador, arquivo)
    return audio, texto, nat, cla


def salvarTts(avaliador, arquivo, naturalidade, clareza):
    if not avaliador or not arquivo:
        raise gr.Error("Escolha o avaliador e o áudio.")
    if naturalidade is None or clareza is None:
        raise gr.Error("Dê as duas notas, de 1 a 5, antes de salvar.")
    linhas = lerTts()
    alvo = next((l for l in linhas if l["avaliador"] == avaliador and l["arquivo"] == arquivo), None)
    if alvo is None:
        raise gr.Error("Linha não encontrada na planilha.")
    alvo["naturalidade"], alvo["clareza"] = str(int(naturalidade)), str(int(clareza))
    gravarTts(linhas)
    proximo = proximoTts(avaliador, arquivo)
    audio, texto, nat, cla = mostrarTts(avaliador, proximo)
    return gr.update(choices=opcoesTts(avaliador), value=proximo), audio, texto, nat, cla, progressoTts()


with gr.Blocks(title="Avaliações humanas") as demo:
    gr.Markdown("# Avaliações humanas\nPreencha sem planilha: cada resposta sua é gravada direto nos arquivos do projeto. "
                "Depois de terminar, rode `python relatorio/gerarRelatorio.py`.")
    with gr.Tab("1. Revisão das respostas do LLM"):
        gr.Markdown("Leia a resposta do assistente e diga se ela está correta, **comparando com a resposta esperada**. "
                    "Nas perguntas fora do escopo, a pergunta é se o assistente recusou como esperado.")
        pergunta = gr.Dropdown(label="Pergunta", choices=[], interactive=True)
        textoLlm = gr.Markdown()
        veredito = gr.Radio(["sim", "nao"], label="A resposta está correta?")
        salvarL = gr.Button("Salvar e ir para a próxima pendente", variant="primary")
        progressoL = gr.Markdown()
    with gr.Tab("2. Notas do TTS"):
        gr.Markdown("Ouça o áudio e dê duas notas de **1 a 5**: **naturalidade** (parece uma pessoa falando?) e "
                    "**clareza** (dá para entender tudo, inclusive números e siglas?). Cada pessoa usa o seu nome de avaliador.")
        avaliador = gr.Radio([], label="Quem está avaliando?")
        arquivo = gr.Dropdown(label="Áudio", choices=[], interactive=True)
        audio = gr.Audio(label="Ouça", interactive=False, type="filepath")
        textoTts = gr.Markdown()
        with gr.Row():
            natural = gr.Radio([1, 2, 3, 4, 5], label="Naturalidade (1 = robótica, 5 = muito natural)")
            clara = gr.Radio([1, 2, 3, 4, 5], label="Clareza (1 = não entendi, 5 = entendi tudo)")
        salvarT = gr.Button("Salvar notas e ir para o próximo", variant="primary")
        progressoT = gr.Markdown()

    pergunta.change(trocarLlm, pergunta, [textoLlm, veredito])
    salvarL.click(salvarLlm, [pergunta, veredito], [pergunta, textoLlm, veredito, progressoL])
    avaliador.change(trocarAvaliador, avaliador, [arquivo, audio, textoTts, natural, clara, progressoT])
    arquivo.change(trocarArquivo, [avaliador, arquivo], [audio, textoTts, natural, clara])
    salvarT.click(salvarTts, [avaliador, arquivo, natural, clara], [arquivo, audio, textoTts, natural, clara, progressoT])

    def iniciar():
        primeira = proximaPendenteLlm(-1)
        texto, atual, rotulo = mostrarLlm(primeira)
        return (gr.update(choices=opcoesLlm(), value=primeira), texto, gr.update(value=atual, label=rotulo), progressoLlm(),
                gr.update(choices=avaliadoresTts()), progressoTts())

    demo.load(iniciar, None, [pergunta, textoLlm, veredito, progressoL, avaliador, progressoT])

if __name__ == "__main__":
    demo.launch(server_port=7862, allowed_paths=[str(pastaTts)])
