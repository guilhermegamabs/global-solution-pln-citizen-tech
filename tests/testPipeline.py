import os

import pipeline


def prepararMocks(monkeypatch, transcricao="estou com tosse", resposta="Descanse e beba água.", tts=None):
    monkeypatch.setattr(pipeline, "transcrever", lambda caminho, modelo=None: transcricao)
    monkeypatch.setattr(pipeline, "responder", lambda historico, texto, modelo=None: resposta)
    monkeypatch.setattr(pipeline, "sintetizar", tts or (lambda fala: "resposta.mp3"))
    monkeypatch.setattr(pipeline, "gravarCsv", lambda registro, origem="app": None)


def criarAudio(tmp_path):
    caminho = tmp_path / "fala.wav"
    caminho.write_bytes(b"audio do cidadao")
    return str(caminho)


def testTurnoCompletoGuardaHistoricoEMedeEtapas(monkeypatch, tmp_path):
    prepararMocks(monkeypatch)
    historico = []
    resultado = pipeline.processarAudio(criarAudio(tmp_path), historico)
    assert resultado["texto"] == "estou com tosse"
    assert resultado["audio"] == "resposta.mp3"
    assert not resultado["semVoz"]
    assert [t["papel"] for t in historico] == ["user", "model"]
    for etapa in ("stt", "llm", "prep", "tts", "total"):
        assert etapa in resultado["latencia"]


def testAudioDoUsuarioEApagadoAposATranscricao(monkeypatch, tmp_path):
    prepararMocks(monkeypatch)
    caminho = criarAudio(tmp_path)
    pipeline.processarAudio(caminho, [])
    assert not os.path.exists(caminho)


def testAudioEApagadoMesmoSeATranscricaoFalhar(monkeypatch, tmp_path):
    prepararMocks(monkeypatch)

    def quebrar(caminho, modelo=None):
        raise RuntimeError("falha no modelo")

    monkeypatch.setattr(pipeline, "transcrever", quebrar)
    caminho = criarAudio(tmp_path)
    try:
        pipeline.processarAudio(caminho, [])
    except RuntimeError:
        pass
    assert not os.path.exists(caminho)


def testApagarAudioPodeSerDesligadoParaOMaterialDeTeste(monkeypatch, tmp_path):
    prepararMocks(monkeypatch)
    caminho = criarAudio(tmp_path)
    pipeline.processarAudio(caminho, [], apagarAudio=False)
    assert os.path.exists(caminho)


def testFalhaNoTtsMantemAResposta(monkeypatch, tmp_path):
    def sinteseQuebrada(fala):
        raise ConnectionError("sem rede")

    prepararMocks(monkeypatch, tts=sinteseQuebrada)
    historico = []
    resultado = pipeline.processarAudio(criarAudio(tmp_path), historico)
    assert resultado["audio"] is None
    assert resultado["semVoz"]
    assert resultado["resposta"] == "Descanse e beba água."
    assert len(historico) == 2


def testTranscricaoVaziaNaoChamaOLlm(monkeypatch, tmp_path):
    prepararMocks(monkeypatch, transcricao="")
    chamadas = []
    monkeypatch.setattr(pipeline, "responder", lambda *a, **k: chamadas.append(1) or "x")
    assert pipeline.processarAudio(criarAudio(tmp_path), []) is None
    assert chamadas == []


def testMemoriaChegaAoLlmNoSegundoTurno(monkeypatch, tmp_path):
    vistos = []
    prepararMocks(monkeypatch)
    monkeypatch.setattr(pipeline, "responder", lambda historico, texto, modelo=None: vistos.append(list(historico)) or "ok")
    historico = []
    pipeline.processarAudio(criarAudio(tmp_path), historico)
    pipeline.processarAudio(criarAudio(tmp_path), historico)
    assert vistos[0] == []
    assert len(vistos[1]) == 2
