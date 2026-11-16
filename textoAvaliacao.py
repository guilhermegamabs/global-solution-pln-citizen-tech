import re

from num2words import num2words


def numerosPorExtenso(texto):
    # o Whisper escreve "39" onde a referência diz "trinta e nove": sem isto o WER pune uma
    # transcrição correta. Só números inteiros; o roteiro não tem decimais.
    return re.sub(r"\d+", lambda m: num2words(int(m.group(0)), lang="pt_BR").replace(",", ""), texto)


def normalizar(texto):
    texto = numerosPorExtenso(texto.lower())
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()
