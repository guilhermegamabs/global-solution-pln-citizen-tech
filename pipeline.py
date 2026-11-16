import os

from latency import fechar, gravarCsv, medir
from llmModule import responder
from speechPrep import prepararFala
from sttModule import transcrever
from ttsModule import sintetizar


def apagarSeExistir(caminho):
    try:
        os.remove(caminho)
    except OSError:
        pass


def processarTexto(texto, historico, registro, modeloLlm=None, origem="app"):
    with medir(registro, "llm"):
        resposta = responder(historico, texto, modeloLlm)
    with medir(registro, "prep"):
        fala = prepararFala(resposta)
    with medir(registro, "tts"):
        try:
            audio = sintetizar(fala)
        except Exception:
            # sem rede para o serviço de voz, por exemplo: a resposta escrita continua útil
            audio = None
    historico.append({"papel": "user", "texto": texto})
    historico.append({"papel": "model", "texto": resposta})
    fechar(registro)
    gravarCsv(registro, origem)
    return {"texto": texto, "resposta": resposta, "fala": fala, "audio": audio, "latencia": registro, "semVoz": audio is None}


def processarAudio(caminhoAudio, historico, modeloStt=None, modeloLlm=None, apagarAudio=True, origem="app"):
    registro = {}
    try:
        with medir(registro, "stt"):
            texto = transcrever(caminhoAudio, modeloStt)
    finally:
        if apagarAudio:
            apagarSeExistir(caminhoAudio)
    if not texto:
        return None
    return processarTexto(texto, historico, registro, modeloLlm, origem)
