"""Página para gravar os 20 áudios do teste de STT (testMaterial/stt/roteiro.csv).

Mostra a frase, grava pelo microfone (ou recebe um arquivo gravado no celular) e salva
testMaterial/stt/audios/sttNN.wav com o nome que o roteiro pede. Também preenche as colunas
de viés do roteiro e guarda o registro de consentimento (só o rótulo da voz e a data).

Uso:  python gravador.py     e abra o endereço mostrado (http://127.0.0.1:7861)
"""
import atexit
import csv
import os
import shutil
import wave
from array import array
from datetime import datetime
from pathlib import Path

from config import pastaTemporaria, raiz

# o que o Gradio recebe fica numa pasta nossa, apagada ao fechar; o áudio final fica só no projeto
pastaGradio = pastaTemporaria() / "gradio-gravador"
shutil.rmtree(pastaGradio, ignore_errors=True)
pastaGradio.mkdir(parents=True, exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = str(pastaGradio)
atexit.register(lambda: shutil.rmtree(pastaGradio, ignore_errors=True))

import av  # noqa: E402
import gradio as gr  # noqa: E402

pastaStt = Path(os.getenv("ORIENTA_STT_DIR", raiz / "testMaterial" / "stt"))
campos = ["arquivo", "voz", "ruido", "textoReferencia", "sexo", "faixaEtaria", "sotaque", "dispositivo"]
duracaoMinima = 1.0
duracaoMaxima = 20.0
picoMinimo = 800  # de 32767: abaixo disso o áudio ficou baixo demais para o Whisper

termoConsentimento = (
    "Concordo que minha voz seja gravada e usada **só** para avaliar este assistente "
    "(teste de reconhecimento de fala da Global Solution de PLN). Os arquivos ficam na pasta do projeto "
    "e podem ser apagados a pedido meu. Não vou dizer nome, CPF nem endereço nas gravações."
)


def carregarRoteiro():
    with open(pastaStt / "roteiro.csv", encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def salvarRoteiro(linhas):
    with open(pastaStt / "roteiro.csv", "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def gravado(item):
    return (pastaStt / "audios" / item["arquivo"]).exists()


def linhasDaVoz(voz):
    return [linha for linha in carregarRoteiro() if linha["voz"] == voz]


def opcoesDaVoz(voz):
    opcoes = []
    for linha in linhasDaVoz(voz):
        marca = "feita" if gravado(linha) else "falta"
        ruido = ", com barulho de fundo" if linha["ruido"] == "sim" else ""
        opcoes.append((f"{linha['arquivo'].replace('.wav', '')} ({marca}{ruido})", linha["arquivo"]))
    return opcoes


def proximaPendente(voz):
    for linha in linhasDaVoz(voz):
        if not gravado(linha):
            return linha["arquivo"]
    linhas = linhasDaVoz(voz)
    return linhas[0]["arquivo"] if linhas else None


def textoDaFrase(arquivo):
    if not arquivo:
        return ""
    for linha in carregarRoteiro():
        if linha["arquivo"] == arquivo:
            aviso = ""
            if linha["ruido"] == "sim":
                aviso = ("\n\n**Esta precisa de barulho de fundo:** deixe uma TV, um ventilador ou a janela "
                         "da rua aberta enquanto grava, como acontece de verdade.")
            return f"### Leia em voz alta, de forma natural:\n\n## {linha['textoReferencia']}{aviso}"
    return ""


def tabelaProgresso():
    linhas = carregarRoteiro()
    feitas = sum(1 for linha in linhas if gravado(linha))
    texto = [f"**{feitas} de {len(linhas)} áudios gravados.**", "", "| Arquivo | Voz | Barulho | Situação |", "|---|---|---|---|"]
    for linha in linhas:
        texto.append(f"| {linha['arquivo']} | {linha['voz']} | {linha['ruido']} | {'feita' if gravado(linha) else 'falta'} |")
    return "\n".join(texto)


def converterParaWav(origem, destino):
    """Qualquer áudio (wav, mp3, m4a do celular, webm do navegador) vira wav mono de 16 kHz."""
    pico = 0
    quadros = 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(origem)) as entrada, wave.open(str(destino), "wb") as saida:
        saida.setnchannels(1)
        saida.setsampwidth(2)
        saida.setframerate(16000)
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

        def escrever(quadro):
            nonlocal pico, quadros
            dados = quadro.to_ndarray().tobytes()
            amostras = array("h")
            amostras.frombytes(dados)
            if amostras:
                pico = max(pico, max(abs(a) for a in amostras))
            quadros += len(amostras)
            saida.writeframes(dados)

        for quadro in entrada.decode(entrada.streams.audio[0]):
            for convertido in resampler.resample(quadro):
                escrever(convertido)
        for convertido in resampler.resample(None):
            escrever(convertido)
    return quadros / 16000, pico


def registrarConsentimento(voz):
    caminho = pastaStt / "consentimentos.csv"
    novo = not caminho.exists()
    if not novo:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            if any(linha.get("voz") == voz for linha in csv.DictReader(arquivo)):
                return
    with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        if novo:
            escritor.writerow(["voz", "data", "termo"])
        escritor.writerow([voz, datetime.now().isoformat(timespec="seconds"), "aceito na tela do gravador"])


def salvarGravacao(voz, arquivo, audio, consentimento, sexo, faixaEtaria, sotaque, dispositivo):
    if not voz:
        raise gr.Error("Escolha quem vai gravar (voz1, voz2 ou voz3).")
    if not consentimento:
        raise gr.Error("Quem vai gravar precisa marcar o consentimento.")
    if not arquivo:
        raise gr.Error("Escolha a frase.")
    if audio is None:
        raise gr.Error("Grave a frase ou envie um arquivo de áudio antes de salvar.")
    destino = pastaStt / "audios" / arquivo
    try:
        duracao, pico = converterParaWav(audio, destino)
    except Exception as erro:
        destino.unlink(missing_ok=True)
        raise gr.Error(f"Não consegui ler esse áudio ({type(erro).__name__}). Tente gravar de novo.")
    avisos = []
    if duracao < duracaoMinima:
        avisos.append(f"o áudio ficou muito curto ({duracao:.1f} s)")
    if duracao > duracaoMaxima:
        avisos.append(f"o áudio ficou muito longo ({duracao:.1f} s)")
    if pico < picoMinimo:
        avisos.append("o volume ficou muito baixo: chegue mais perto do microfone")
    if avisos:
        destino.unlink(missing_ok=True)
        raise gr.Error("Não salvei porque " + " e ".join(avisos) + ". Grave de novo.")

    # dados de viés valem para todas as frases dessa voz
    linhas = carregarRoteiro()
    for linha in linhas:
        if linha["voz"] == voz:
            for nome, valor in (("sexo", sexo), ("faixaEtaria", faixaEtaria), ("sotaque", sotaque), ("dispositivo", dispositivo)):
                if valor:
                    linha[nome] = valor
    salvarRoteiro(linhas)
    registrarConsentimento(voz)

    proxima = proximaPendente(voz)
    mensagem = f"Salvo: {arquivo} ({duracao:.1f} s). "
    mensagem += "Todas as frases desta voz estão gravadas." if all(gravado(linha) for linha in linhasDaVoz(voz)) else "Próxima frase já selecionada."
    return (mensagem, gr.update(choices=opcoesDaVoz(voz), value=proxima), textoDaFrase(proxima), tabelaProgresso(), None)


def conferirComWhisper(arquivo):
    """Transcreve o áudio salvo e compara com a frase: serve para pegar gravação ruim na hora."""
    import jiwer

    from sttModule import transcrever
    from textoAvaliacao import normalizar

    if not arquivo or not (pastaStt / "audios" / arquivo).exists():
        raise gr.Error("Essa frase ainda não foi gravada.")
    referencia = next(linha["textoReferencia"] for linha in carregarRoteiro() if linha["arquivo"] == arquivo)
    hipotese = transcrever(pastaStt / "audios" / arquivo)
    erro = jiwer.wer(normalizar(referencia), normalizar(hipotese))
    return f"**Frase:** {referencia}\n\n**O Whisper entendeu:** {hipotese}\n\n**WER desta frase:** {erro:.2f} (0 é perfeito)"


def trocarVoz(voz):
    proxima = proximaPendente(voz) if voz else None
    return gr.update(choices=opcoesDaVoz(voz) if voz else [], value=proxima), textoDaFrase(proxima), tabelaProgresso()


with gr.Blocks(title="Gravador do teste de STT") as demo:
    gr.Markdown(
        "# Gravador do teste de STT\n"
        "Cada pessoa grava as frases dela, uma por vez. O áudio é salvo em `testMaterial/stt/audios/` "
        "com o nome certo. Dá para gravar pelo microfone daqui ou enviar um arquivo gravado no celular."
    )
    gr.Markdown(f"**Termo de consentimento.** {termoConsentimento}")
    with gr.Row():
        voz = gr.Radio(["voz1", "voz2", "voz3"], label="Quem vai gravar agora?")
        consentimento = gr.Checkbox(label="Esta pessoa leu o termo e concorda")
    with gr.Row():
        sexo = gr.Dropdown(["feminino", "masculino", "prefiro não informar"], label="Sexo", value=None)
        faixaEtaria = gr.Dropdown(["18 a 29", "30 a 44", "45 a 59", "60 ou mais"], label="Faixa etária", value=None)
        sotaque = gr.Textbox(label="Sotaque ou região (ex.: paulistano, nordestino)")
        dispositivo = gr.Textbox(label="Aparelho usado (ex.: notebook, celular X)")
    frase = gr.Dropdown(label="Frase", choices=[], interactive=True)
    textoFrase = gr.Markdown()
    entrada = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Grave (ou envie um arquivo)")
    with gr.Row():
        salvar = gr.Button("Salvar esta frase", variant="primary")
        conferir = gr.Button("Conferir com o Whisper")
    status = gr.Markdown()
    resultado = gr.Markdown()
    progresso = gr.Markdown(tabelaProgresso())

    voz.change(trocarVoz, voz, [frase, textoFrase, progresso])
    frase.change(textoDaFrase, frase, textoFrase)
    salvar.click(salvarGravacao, [voz, frase, entrada, consentimento, sexo, faixaEtaria, sotaque, dispositivo],
                 [status, frase, textoFrase, progresso, entrada])
    conferir.click(conferirComWhisper, frase, resultado)

if __name__ == "__main__":
    demo.launch(server_port=7861)
