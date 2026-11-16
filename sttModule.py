from faster_whisper import WhisperModel

from config import dispositivoWhisper, modeloWhisper, threadsWhisper

modelosCarregados = {}
gpuIndisponivel = False


def carregar(tamanho, dispositivo):
    chave = (tamanho, dispositivo)
    if chave not in modelosCarregados:
        # int8 na CPU: é o tipo de cálculo que o faster-whisper recomenda para rodar sem GPU
        tipo = "int8" if dispositivo == "cpu" else "auto"
        modelosCarregados[chave] = WhisperModel(tamanho, device=dispositivo, compute_type=tipo,
                                                cpu_threads=threadsWhisper())
    return modelosCarregados[chave]


def rodar(modelo, caminhoAudio):
    # o transcribe devolve um gerador: o erro de GPU só aparece ao consumir os segmentos
    segmentos, dados = modelo.transcribe(
        str(caminhoAudio),
        language="pt",
        beam_size=5,
        vad_filter=True,
    )
    return " ".join(segmento.text.strip() for segmento in segmentos).strip()


def transcrever(caminhoAudio, tamanho=None):
    global gpuIndisponivel
    tamanho = tamanho or modeloWhisper()
    dispositivo = "cpu" if gpuIndisponivel else dispositivoWhisper()
    try:
        return rodar(carregar(tamanho, dispositivo), caminhoAudio)
    except RuntimeError as erro:
        if dispositivo == "cpu":
            raise
        # GPU visível, mas sem as bibliotecas CUDA (cublas/cudnn): cai para a CPU
        # em vez de derrubar a conversa, e não tenta a GPU de novo nesta sessão.
        print(f"Whisper: GPU indisponível ({erro}); usando CPU.")
        gpuIndisponivel = True
        return rodar(carregar(tamanho, "cpu"), caminhoAudio)
