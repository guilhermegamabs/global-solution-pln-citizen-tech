import asyncio
import tempfile
import time
from pathlib import Path

import edge_tts

from config import pastaTemporaria, vozTts

validadeRespostaSegundos = 600


async def gravarAudio(texto, caminho, voz):
    await edge_tts.Communicate(texto, voz).save(str(caminho))


def apagarRespostasAntigas(pasta, validade=validadeRespostaSegundos):
    # a resposta falada só precisa existir até o navegador tocar; sem isso os mp3 se acumulam
    limite = time.time() - validade
    for arquivo in pasta.glob("orientaTts*.mp3"):
        try:
            if arquivo.stat().st_mtime < limite:
                arquivo.unlink()
        except OSError:
            pass


def sintetizar(texto, caminhoSaida=None, voz=None):
    if caminhoSaida is None:
        pasta = pastaTemporaria() / "respostas"
        pasta.mkdir(exist_ok=True)
        apagarRespostasAntigas(pasta)
        arquivo = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, prefix="orientaTts", dir=pasta)
        arquivo.close()
        caminhoSaida = arquivo.name
    caminho = Path(caminhoSaida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(gravarAudio(texto, caminho, voz or vozTts()))
    return str(caminho)
