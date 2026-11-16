import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

raiz = Path(__file__).resolve().parent
load_dotenv(raiz / ".env")


def chaveGemini():
    return os.getenv("GEMINIAPIKEY", "")


def modeloGemini():
    return os.getenv("GEMINIMODEL", "gemini-2.5-flash")


def modeloWhisper():
    return os.getenv("WHISPERMODEL", "small")


def dispositivoWhisper():
    # "auto" usa a GPU quando existir e cai para a CPU se faltar biblioteca CUDA;
    # "cpu" ou "cuda" forçam o dispositivo.
    return os.getenv("WHISPERDEVICE", "auto")


def threadsWhisper():
    # 0 deixa o faster-whisper decidir; um número limita os núcleos da CPU usados pelo STT
    return int(os.getenv("WHISPERTHREADS", "0"))


def vozTts():
    return os.getenv("TTSVOICE", "pt-BR-FranciscaNeural")


def pastaTemporaria():
    # tudo que o assistente grava por pouco tempo (respostas faladas, cache do Gradio) fica aqui,
    # para dar para apagar de uma vez e para verificar que não sobra áudio do cidadão
    pasta = Path(tempfile.gettempdir()) / "orienta-saude-voz"
    pasta.mkdir(exist_ok=True)
    return pasta


def limparPastaTemporaria():
    shutil.rmtree(pastaTemporaria(), ignore_errors=True)


def pastaLogs():
    pasta = raiz / "logs"
    pasta.mkdir(exist_ok=True)
    return pasta


def pastaResultados():
    pasta = raiz / "resultados"
    pasta.mkdir(exist_ok=True)
    return pasta
