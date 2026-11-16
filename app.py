import atexit
import os

from config import limparPastaTemporaria, pastaTemporaria

# O Gradio guarda o que recebe numa pasta temporária. Apontar para uma pasta nossa permite
# apagá-la ao abrir e ao fechar o app, para não sobrar áudio de ninguém.
limparPastaTemporaria()
pastaGradio = pastaTemporaria() / "gradio"
pastaGradio.mkdir(exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = str(pastaGradio)
atexit.register(limparPastaTemporaria)

import gradio as gr

from llmModule import ErroLlm
from pipeline import processarAudio

avisoPrivacidade = (
    "**Antes de começar:** sua voz é um dado pessoal. Ao usar este assistente, você concorda que a conversa "
    "seja **gravada e processada**: o áudio é transcrito localmente, na máquina que roda o assistente (Whisper), e **o texto da transcrição "
    "é enviado ao Google (Gemini)** para gerar a resposta, que depois vira áudio pelo serviço de voz da Microsoft "
    "(edge-tts). O áudio que você grava é **apagado logo após a transcrição**. Não informe nome, CPF ou endereço. "
    "Este assistente orienta, não diagnostica e não substitui um profissional de saúde. "
    "Em emergência, ligue **192**."
)

tema = gr.themes.Soft(primary_hue="blue", secondary_hue="sky")


def formatarLatencia(latencia):
    linhas = ["| Etapa | Segundos |", "|---|---|"]
    nomes = {"stt": "Transcrição (STT)", "llm": "Modelo de linguagem", "prep": "Adaptação para fala", "tts": "Síntese de voz (TTS)", "total": "Total até a fala"}
    for chave, nome in nomes.items():
        linhas.append(f"| {nome} | {latencia.get(chave, 0):.2f} |")
    return "\n".join(linhas)


def conversar(audio, aceite, historico, chat):
    if not aceite:
        raise gr.Error("Marque que leu o aviso de privacidade para continuar.")
    if audio is None:
        raise gr.Error("Grave ou envie um áudio antes de enviar.")
    try:
        resultado = processarAudio(audio, historico)
    except ErroLlm as erro:
        raise gr.Error(str(erro))
    if resultado is None:
        raise gr.Error("Não consegui entender o áudio. Tente falar mais perto do microfone.")
    if resultado["semVoz"]:
        gr.Warning("Não consegui gerar a voz agora. A resposta está escrita na tela.")
    chat = chat + [
        {"role": "user", "content": resultado["texto"]},
        {"role": "assistant", "content": resultado["resposta"]},
    ]
    return chat, historico, resultado["audio"], formatarLatencia(resultado["latencia"]), None


def reiniciar():
    return [], [], None, "", None


# delete_cache: a cada 5 min apaga do cache do Gradio o que tiver mais de 10 min (resposta falada)
with gr.Blocks(title="Orienta Saúde Voz", theme=tema, delete_cache=(300, 600)) as demo:
    gr.Markdown("# Orienta Saúde Voz\nFale o que você está sentindo e ouça para onde ir: casa, UBS, UPA ou SAMU.")
    gr.Markdown(avisoPrivacidade)
    aceite = gr.Checkbox(label="Li o aviso e concordo com a gravação e o processamento da conversa")
    historico = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            entrada = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Aperte para gravar ou envie um arquivo de áudio",
            )
            enviar = gr.Button("Enviar", variant="primary")
            novo = gr.Button("Nova conversa")
            saida = gr.Audio(label="Resposta falada", autoplay=True, interactive=False)
            latencia = gr.Markdown()
        with gr.Column(scale=1):
            chat = gr.Chatbot(type="messages", label="Transcrição e resposta", height=480)
    enviar.click(conversar, [entrada, aceite, historico, chat], [chat, historico, saida, latencia, entrada])
    novo.click(reiniciar, None, [chat, historico, saida, latencia, entrada])

demo.launch()
