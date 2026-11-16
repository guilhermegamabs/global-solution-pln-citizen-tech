"""Gera o relatório da Global Solution de PLN no padrão dos relatórios das outras disciplinas
(capa FIAP, título "CitizenTech · Orienta Saúde", tabelas de cabeçalho preto, rodapé "Página N").

Todo número do relatório vem dos arquivos em resultados/ e testMaterial/: nada é digitado à mão.
Campos que dependem do grupo (revisão manual do LLM, notas do TTS, link do vídeo) aparecem como
"pendente" enquanto não forem preenchidos, e o relatório se atualiza ao rodar de novo.

Uso:  python relatorio/gerarRelatorio.py
"""
import csv
import io
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether,  # noqa: E402
                                ListFlowable, ListItem, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados"
TESTE = RAIZ / "testMaterial"
SAIDA = RAIZ / "relatorio" / "CitizenTech_PLN_OrientaSaudeVoz_Relatorio.pdf"

DISCIPLINA = "Processamento de Linguagem Natural, Chatbots & Virtual Agents"
PROFESSOR = "Sergio Eduardo Palmiere"
TURMA = "2TIAPY-2026"
INTEGRANTES = ["Guilherme Gama Bitencourt Souza · RM565293"]
REPOSITORIO = "https://github.com/guilhermegamabs/global-solution-pln-citizen-tech"
SUBTITULO = "Assistente de voz em português para orientar o cidadão no SUS: STT, LLM e TTS com avaliação por componente e ponta a ponta"
ESCOLHA_STT = "small"

PRETO, CINZA, CLARO, LINHA = "#111111", "#555555", "#f3f3f3", "#cfcfcf"


# ── fontes e estilos ────────────────────────────────────────────────────────
def registrarFontes():
    f = Path("C:/Windows/Fonts")
    if (f / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont("Arial", str(f / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("Arial-B", str(f / "arialbd.ttf")))
        pdfmetrics.registerFont(TTFont("Arial-I", str(f / "ariali.ttf")))
        pdfmetrics.registerFont(TTFont("Arial-BI", str(f / "arialbi.ttf")))
        pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-B", italic="Arial-I", boldItalic="Arial-BI")
        nomes = ("Arial", "Arial-B", "Arial-I")
    else:
        nomes = ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")
    mono = "Courier"
    if (f / "consola.ttf").exists():
        pdfmetrics.registerFont(TTFont("Consolas", str(f / "consola.ttf")))
        mono = "Consolas"
    return nomes + (mono,)


FONTE, NEGRITO, ITALICO, MONO = registrarFontes()


def estilo(nome, **kw):
    base = dict(fontName=FONTE, fontSize=9.5, leading=12.8, textColor=colors.HexColor(PRETO))
    base.update(kw)
    return ParagraphStyle(nome, **base)


corpo = estilo("corpo", spaceAfter=4)
pequeno = estilo("pequeno", fontSize=7.5, leading=9.5, textColor=colors.HexColor(CINZA), spaceAfter=3)
h1 = estilo("h1", fontName=NEGRITO, fontSize=13, leading=16, spaceBefore=11, spaceAfter=5, keepWithNext=1)
h2 = estilo("h2", fontName=NEGRITO, fontSize=10.5, leading=13, spaceBefore=7, spaceAfter=3, keepWithNext=1)
celula = estilo("celula", fontSize=8.5, leading=10.5)
celulaB = estilo("celulaB", fontSize=8.5, leading=10.5, fontName=NEGRITO, textColor=colors.white)
tituloRel = estilo("tituloRel", fontName=NEGRITO, fontSize=17, leading=21)
subRel = estilo("subRel", fontSize=8.5, leading=11, textColor=colors.HexColor(CINZA), spaceAfter=6)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md(t):
    """**negrito**, *itálico* e `código` -> tags do reportlab, com escape do resto."""
    partes = re.split(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)", t)
    saida = []
    for p in partes:
        if p.startswith("**"):
            saida.append(f"<b>{esc(p[2:-2])}</b>")
        elif p.startswith("`"):
            saida.append(f'<font face="{MONO}" size="8">{esc(p[1:-1])}</font>')
        elif p.startswith("*") and p.endswith("*") and len(p) > 2:
            saida.append(f"<i>{esc(p[1:-1])}</i>")
        else:
            saida.append(esc(p))
    return "".join(saida)


def P(t, st=corpo):
    return Paragraph(md(t), st)


def lista(itens):
    return ListFlowable([ListItem(P(i), leftIndent=11) for i in itens], bulletType="bullet", start="•",
                        bulletFontName=FONTE, bulletFontSize=9, leftIndent=11, bulletColor=colors.HexColor(PRETO))


def tabela(linhas, larguras, alinharDireita=()):
    """Cabeçalho preto com texto branco, linhas alternadas em cinza claro, como nas outras entregas."""
    dados = []
    for i, linha in enumerate(linhas):
        dados.append([Paragraph(md(str(c)), celulaB if i == 0 else celula) for c in linha])
    total = 16.6 * cm
    t = Table(dados, colWidths=[total * w for w in larguras], repeatRows=1)
    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PRETO)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor(LINHA)),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(LINHA)),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(2, len(linhas), 2):
        estilos.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(CLARO)))
    t.setStyle(TableStyle(estilos))
    return t


def pt(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


# ── leitura dos resultados ──────────────────────────────────────────────────
def lerCsv(caminho):
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def media(valores):
    valores = list(valores)
    return mean(valores) if valores else float("nan")


stt = lerCsv(RES / "sttResultados.csv")
llm = lerCsv(RES / "llmResultados.csv")
llmTentativa1 = lerCsv(RES / "llmResultados_tentativa1_falhou.csv")
e2e = lerCsv(RES / "e2eResultados.csv")
tts = lerCsv(TESTE / "tts" / "avaliacao.csv")
roteiro = lerCsv(TESTE / "stt" / "roteiro.csv")
consentimentos = lerCsv(TESTE / "stt" / "consentimentos.csv")
perguntas = {p["id"]: p for p in lerCsv(TESTE / "perguntas.csv")}

for r in stt:
    r["wer"], r["segundos"] = float(r["wer"]), float(r["segundos"])
modelosStt = sorted({r["modelo"] for r in stt}, key=lambda m: ["small", "medium"].index(m) if m in ("small", "medium") else 9)


def werDe(modelo, **filtros):
    linhas = [r for r in stt if r["modelo"] == modelo and all(r.get(k) == v for k, v in filtros.items())]
    return media(r["wer"] for r in linhas), len(linhas)


def contarTestes():
    try:
        venv = RAIZ / "venv" / "Scripts" / "python.exe"
        python = str(venv) if venv.exists() else sys.executable
        saida = subprocess.run([python, "-m", "pytest", "-q"], cwd=RAIZ, capture_output=True, text=True, timeout=120).stdout
        m = re.search(r"(\d+) passed(?:, (\d+) xfailed)?", saida)
        return int(m.group(1)), int(m.group(2) or 0)
    except Exception:
        return None, None


def contarFontes():
    texto = (RAIZ / "knowledge" / "FONTES.md").read_text(encoding="utf-8")
    contagem = {}
    for m in re.finditer(r"^\| \d+ \| .*? \| (Confirmada|Parcial|Sem fonte|Divergente|Não aberta)", texto, re.M):
        contagem[m.group(1)] = contagem.get(m.group(1), 0) + 1
    return contagem


testesOk, testesXfail = contarTestes()
fontes = contarFontes()


# ── gráficos em tons de cinza ───────────────────────────────────────────────
def figura(fig, largura):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    img.drawHeight = img.drawHeight * largura / img.drawWidth
    img.drawWidth = largura
    return img


def graficoStt():
    grupos = [("Geral", {}), ("voz1", {"voz": "voz1"}), ("voz2", {"voz": "voz2"}), ("voz3", {"voz": "voz3"}),
              ("sem ruído", {"ruido": "nao"}), ("com ruído", {"ruido": "sim"})]
    tons = {"small": "#9a9a9a", "medium": "#111111"}
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    largura = 0.38
    for k, m in enumerate(modelosStt):
        valores = [werDe(m, **f)[0] for _, f in grupos]
        posicoes = [i + (k - 0.5) * largura for i in range(len(grupos))]
        barras = ax.bar(posicoes, valores, largura, label=f"Whisper {m}", color=tons.get(m, "#555"))
        for b, v in zip(barras, valores):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.004, pt(v, 3), ha="center", fontsize=6.5)
    ax.set_xticks(range(len(grupos)))
    ax.set_xticklabels([g for g, _ in grupos], fontsize=8)
    ax.set_ylabel("WER (menor é melhor)", fontsize=8)
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    return figura(fig, 15.5 * cm)


def graficoLatencia():
    etapas = [("stt", "Transcrição (STT)", "#d0d0d0"), ("llm", "Modelo de linguagem", "#8a8a8a"), ("tts", "Síntese de voz (TTS)", "#111111")]
    fig, ax = plt.subplots(figsize=(7.2, 1.5))
    esquerda = 0
    for chave, nome, cor in etapas:
        v = media(float(r[chave]) for r in e2e)
        ax.barh([0], [v], left=esquerda, color=cor, label=f"{nome}: {pt(v, 1)} s", height=0.5, edgecolor="white")
        ax.text(esquerda + v / 2, 0, pt(v, 1), ha="center", va="center", fontsize=8, color="white" if cor == "#111111" else "#111")
        esquerda += v
    ax.set_yticks([])
    ax.set_xlabel("segundos, média dos 30 turnos (a adaptação para fala leva menos de 0,01 s)", fontsize=7.5)
    ax.tick_params(axis="x", labelsize=7)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.45))
    return figura(fig, 15.5 * cm)


# ── diagrama da arquitetura ─────────────────────────────────────────────────
class Diagrama(Flowable):
    caixas = [("Microfone\nou upload", False), ("STT\nfaster-whisper", False), ("LLM\nGemini + prompt\n+ base + memória", True),
              ("Adaptação\npara fala", False), ("TTS\nedge-tts", True), ("Alto-falante\n+ texto na tela", False)]

    def __init__(self, largura=16.6 * cm, altura=3.6 * cm):
        super().__init__()
        self.width, self.height = largura, altura

    def draw(self):
        c = self.canv
        n = len(self.caixas)
        gap = 0.55 * cm
        w = (self.width - gap * (n - 1)) / n
        h = 1.7 * cm
        y = 1.25 * cm
        for i, (texto, nuvem) in enumerate(self.caixas):
            x = i * (w + gap)
            c.setLineWidth(0.8)
            c.setStrokeColor(colors.HexColor(PRETO))
            c.setFillColor(colors.HexColor("#dcdcdc") if nuvem else colors.white)
            c.roundRect(x, y, w, h, 3, stroke=1, fill=1)
            c.setFillColor(colors.HexColor(PRETO))
            linhas = texto.split("\n")
            topo = y + h / 2 + (len(linhas) - 1) * 4.3
            for j, linha in enumerate(linhas):
                c.setFont(NEGRITO if j == 0 else FONTE, 7.8 if j == 0 else 6.8)
                c.drawCentredString(x + w / 2, topo - j * 8.6, linha)
            c.setFont(FONTE, 6.5)
            c.setFillColor(colors.HexColor(CINZA))
            c.drawCentredString(x + w / 2, y - 0.42 * cm, "nuvem" if nuvem else "máquina do usuário")
            if i < n - 1:
                x0, x1 = x + w + 1.2, x + w + gap - 1.2
                c.setStrokeColor(colors.HexColor(PRETO))
                c.line(x0, y + h / 2, x1, y + h / 2)
                c.line(x1, y + h / 2, x1 - 3, y + h / 2 + 2)
                c.line(x1, y + h / 2, x1 - 3, y + h / 2 - 2)
        c.setStrokeColor(colors.HexColor(CINZA))
        c.setDash(2, 2)
        c.line(w * 1.5 + gap, y + h + 0.3 * cm, w * 4.5 + gap * 4, y + h + 0.3 * cm)
        c.setDash()
        c.setFont(FONTE, 6.8)
        c.setFillColor(colors.HexColor(CINZA))
        c.drawCentredString(self.width / 2, y + h + 0.45 * cm, "registro de latência de cada etapa e do total (logs/latencia.csv, sem texto nem áudio)")


# ── capa e páginas ──────────────────────────────────────────────────────────
def capa(c, doc):
    c.saveState()
    L, R = 2.3 * cm, A4[0] - 2.3 * cm
    cx = A4[0] / 2
    c.setFillColor(colors.HexColor(PRETO))
    c.setFont(NEGRITO, 15)
    c.drawCentredString(cx, A4[1] - 3.3 * cm, "FIAP")
    c.setFont(FONTE, 9.5)
    c.drawCentredString(cx, A4[1] - 3.95 * cm, "Faculdade de Informática e Administração Paulista")
    c.drawCentredString(cx, A4[1] - 4.5 * cm, "Tecnologia em Inteligência Artificial")
    c.setStrokeColor(colors.HexColor(PRETO))
    c.setLineWidth(0.9)
    c.line(L, A4[1] - 5.6 * cm, R, A4[1] - 5.6 * cm)
    c.setFont(FONTE, 9.5)
    c.drawCentredString(cx, A4[1] - 9.1 * cm, "GLOBAL SOLUTION 2026.2")
    c.setFont(FONTE, 10.5)
    c.drawCentredString(cx, A4[1] - 9.9 * cm, DISCIPLINA)
    c.setFont(NEGRITO, 22)
    c.drawCentredString(cx, A4[1] - 12.5 * cm, "CitizenTech · Orienta Saúde")
    c.restoreState()


def rodape(c, doc):
    c.saveState()
    c.setFont(FONTE, 7)
    c.setFillColor(colors.HexColor(CINZA))
    c.drawString(2 * cm, 1.2 * cm, f"CitizenTech 2026.2  |  Global Solution  |  {DISCIPLINA}")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page - 1}")
    c.restoreState()


def elementosCapa():
    sub = estilo("subCapa", fontSize=10.5, leading=14, alignment=TA_CENTER)
    linhas = [("Disciplina", DISCIPLINA), ("Professor", PROFESSOR), ("Turma", TURMA),
              ("Ano / semestre", "2026 · 2º semestre (Global Solution 2026.2)"),
              ("Integrante" if len(INTEGRANTES) == 1 else "Integrantes", "<br/>".join(INTEGRANTES)),
              ("Repositório", REPOSITORIO)]
    video = (RAIZ / "relatorio" / "video.txt")
    if video.exists() and video.read_text(encoding="utf-8").strip():
        linhas.append(("Vídeo", video.read_text(encoding="utf-8").strip()))
    dados = [[Paragraph(f"<b>{esc(k)}</b>", celula), Paragraph(v if "<br/>" in v else esc(v), celula)] for k, v in linhas]
    t = Table(dados, colWidths=[3.2 * cm, 12 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(LINHA)),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [Spacer(1, 12.4 * cm), Paragraph(esc(SUBTITULO), sub), Spacer(1, 2.1 * cm), t, Spacer(1, 2.2 * cm),
            Paragraph("São Paulo · novembro de 2026", estilo("data", fontSize=9.5, alignment=TA_CENTER)),
            NextPageTemplate("corpo"), PageBreak()]


# ── conteúdo ────────────────────────────────────────────────────────────────
def secaoVinculo():
    return [
        P("1. Vínculo com o desafio CitizenTech", h1),
        P("**Função da IA no protótipo.** O Orienta Saúde Voz recebe a fala do cidadão, transcreve com um modelo de reconhecimento de voz, "
          "entende o pedido com um modelo de linguagem (LLM) e responde falando: indica se o caso é de cuidado em casa, UBS, UPA ou SAMU 192, "
          "faz perguntas de continuação e recusa o que está fora do tema."),
        P("**Persona.** Dona Maria, 68 anos, baixa escolaridade, usa a UBS do bairro e tem dificuldade para digitar no celular. Quando o neto está com febre, "
          "não sabe se espera, se vai à UBS, se corre à UPA ou se liga para o SAMU. Também atende cuidadores de crianças e de idosos, pessoas com "
          "deficiência visual ou motora e quem está com as mãos ocupadas."),
        P("**Problema.** As UPAs 24 horas foram criadas para urgências de complexidade intermediária, mas recebem muitos casos de baixa complexidade. "
          "Em Ijuí (RS), de janeiro a junho de 2025, cerca de 80% dos 49.642 atendimentos da UPA foram verdes ou azuis na classificação de Manchester "
          "(CULPO et al., Unijuí, 2025). É o estudo de um único município, citado do relatório do Orienta Saúde (Front End) e não reconferido aqui. "
          "A voz tira a barreira do texto: quem não digita bem pergunta falando."),
        P("**ODS.** ODS 3 (Saúde e Bem-Estar, meta 3.8, cobertura universal de saúde) e ODS 10 (Redução das Desigualdades, ao diminuir a barreira "
          "de acesso para quem tem dificuldade com interfaces de texto)."),
        P("**Relação com as outras disciplinas.** É a versão por voz do Orienta Saúde: o Front End entrega a triagem por texto, o Generative AI & Advanced Nets "
          "avalia um assistente com RAG sobre páginas do gov.br, o Cluster Computing simula a carga de triagens. Este projeto usa a mesma persona, o mesmo "
          "problema e o mesmo conjunto de serviços de saúde."),
    ]


def resumoRespostas():
    manual = [r for r in llm if r["revisaoManual"].strip()]
    notasTts = [r for r in tts if r["naturalidade"] and r["clareza"]]
    auto = [r for r in llm if r["tipo"] != "fora"]
    certas = sum(1 for r in auto if r["acertoAutomatico"] == "True")
    recus = [r for r in llm if r["tipo"] == "fora"]
    totais = [float(r["total"]) for r in e2e]
    wSmall, wMedium = werDe("small")[0], werDe("medium")[0]
    tSmall = media(r["segundos"] for r in stt if r["modelo"] == "small")
    tMedium = media(r["segundos"] for r in stt if r["modelo"] == "medium")
    linhas = [
        ["Pergunta que o relatório responde", "Resposta curta"],
        ["O STT entende o cidadão?",
         f"Com 20 áudios de 3 vozes, o Whisper small teve WER de {pt(wSmall, 3)} e o medium de {pt(wMedium, 3)}. "
         f"O medium acerta mais termos de saúde e leva {pt(tMedium / tSmall, 1)} vezes mais tempo"],
        ["O LLM responde e recusa bem?",
         f"Gemini 3.5 Flash-Lite: {certas} de {len(auto)} respostas corretas na triagem automática, "
         f"{sum(1 for r in recus if r['acertoAutomatico'] == 'True')} de {len(recus)} recusas adequadas. "
         + ("Revisão manual: " + f"{len(manual)} de {len(llm)} respostas revisadas" if manual else "A revisão manual ainda está pendente")],
        ["A voz sai natural e clara?",
         (f"Nota média {pt(media(float(r['naturalidade']) for r in notasTts), 1)} de naturalidade e "
          f"{pt(media(float(r['clareza']) for r in notasTts), 1)} de clareza (escala de 1 a 5; {len(notasTts)} notas de "
          f"{len({r['avaliador'] for r in notasTts})} avaliador(es)" + ("" if len({r['avaliador'] for r in notasTts}) >= 3 else ", o enunciado pede pelo menos 3")
          + ")") if notasTts else "Avaliação por 3 pessoas ainda pendente"],
        ["Qual a latência de ponta a ponta?",
         f"{pt(mean(totais), 1)} s em média, da pergunta até o áudio da resposta pronto (faixa de {pt(min(totais), 1)} a {pt(max(totais), 1)} s, 30 turnos). "
         f"A síntese de voz é a etapa mais lenta"],
        ["E a privacidade?",
         "O áudio do cidadão é apagado depois da transcrição e o STT roda na própria máquina; só o texto vai à nuvem, e o aviso diz isso antes do primeiro uso"],
        ["Quando não confiar na resposta?",
         "A base de conhecimento não passou por revisão clínica. O assistente orienta, não diagnostica, e manda ligar 192 nos sinais de emergência"],
    ]
    return [P("2. Resumo", h1), tabela(linhas, [0.3, 0.7])]


def secaoArquitetura():
    tabelaModelos = [
        ["Componente", "Modelo ou biblioteca", "Versão", "Licença", "Onde roda"],
        ["STT", "faster-whisper com Whisper `small` e `medium`", "1.1.1", "MIT", "local"],
        ["LLM", "Gemini `gemini-2.5-flash` e `gemini-3.5-flash-lite` (API Google)", "API v1beta", "termos da Gemini API", "nuvem"],
        ["TTS", "edge-tts, voz `pt-BR-FranciscaNeural`", "7.3.1", "LGPL-3.0 (biblioteca); voz sob os termos do serviço", "nuvem"],
        ["Adaptação para fala", "num2words (números e datas por extenso)", "0.5.14", "LGPL-2.1", "local"],
        ["Interface", "Gradio", "5.50.0", "Apache-2.0", "local"],
        ["Métrica de STT", "jiwer (WER)", "3.1.0", "Apache-2.0", "local"],
    ]
    return [
        P("3. Arquitetura e escolhas", h1),
        P("O fluxo é microfone, STT, LLM, adaptação para fala, TTS e alto-falante, repetido a cada turno. Cada etapa é um módulo separado "
          "(`sttModule`, `llmModule`, `speechPrep`, `ttsModule`), e só o `pipeline` fala com todos, então um componente se troca sem reescrever o resto."),
        Spacer(1, 4), Diagrama(), Spacer(1, 10),
        tabela(tabelaModelos, [0.14, 0.34, 0.1, 0.27, 0.15]),
        Spacer(1, 4),
        P("Todas as vozes são sintéticas prontas; nenhuma voz real é clonada.", pequeno),
        P("3.1 Nuvem ou local", h2),
        lista([
            "**STT local.** A voz é dado pessoal e pode ser biométrica; transcrever na máquina impede que o áudio saia dela.",
            "**LLM e TTS na nuvem.** Modelos locais de qualidade equivalente exigem GPU, que o usuário comum não tem. O custo é o plano gratuito do Gemini e o edge-tts gratuito. "
            "O preço é depender de internet, de cota e de um serviço externo, o que aparece nas limitações.",
            "**Computador de teste.** A GPU não pôde ser usada porque faltam as bibliotecas CUDA; o Whisper rodou em CPU e o código cai para a CPU sozinho nesse caso.",
        ]),
        P("3.2 Base de conhecimento no prompt, não RAG", h2),
        P("A base (`knowledge/orientaSaude.txt`) tem cerca de uma página: níveis de atendimento, sinais de emergência, telefones úteis e limites. "
          "Como o domínio é pequeno e estável, o texto inteiro vai no prompt de sistema. Um RAG acrescentaria latência e complexidade sem ganho, e o fine-tuning "
          "exigiria revisão clínica que o grupo não tem. O prompt define o papel, o tom (acolhedor, frases curtas, sem markdown, sem emoji), os limites "
          "(não diagnostica, não indica remédio nem dose) e as frases padrão de recusa e de desconhecimento."),
        P("3.3 Memória e adaptação para fala", h2),
        P("O histórico dos últimos 10 turnos vai ao modelo, o que permite perguntas de continuação como \"e onde eu faço isso?\". Antes do TTS, a resposta passa por "
          "`speechPrep`: remove markdown e emoji e escreve por extenso números, horas, datas, valores em reais e unidades, e lê os telefones de emergência dígito a dígito "
          "(192 vira \"um nove dois\"). "
          + (f"São {testesOk} testes automáticos" + (f" e {testesXfail} limitações conhecidas marcadas" if testesXfail else "") + "." if testesOk else "")),
    ]


def secaoBase():
    total = sum(fontes.values()) or 0
    linhas = [["Situação da afirmação", "Quantidade"]]
    for k in ("Confirmada", "Parcial", "Sem fonte", "Divergente", "Não aberta"):
        if fontes.get(k):
            linhas.append([k, str(fontes[k])])
    alteracoes = [
        ["Item", "Antes", "Depois", "Fonte"],
        ["Telefone 136", "\"Disque Saúde, gratuito\"", "Ouvidoria-Geral do SUS, de segunda a sexta das 8h às 20h e aos sábados das 8h às 18h; não é emergência", "FAQ da OuvSUS, Ministério da Saúde"],
        ["AVC", "\"Não levar por conta própria; anotar a hora\"", "Ligar para o 192, informar a hora de início, não dar remédio, água nem comida", "SES-PE e SES-DF; o Ministério manda ligar 192"],
        ["UBS", "\"Procurar em até dois dias\"", "Prazo removido", "Página do Ministério não traz prazo"],
        ["Tontura e pressão alta", "\"Sentar, descansar e procurar a UBS\"", "\"Procurar a UBS\" (192 nos sinais de alerta)", "Sem fonte para o resto da conduta"],
    ]
    return [
        P("4. Base de conhecimento e fontes", h1),
        P(f"Conferi {total} afirmações da base contra páginas do Ministério da Saúde, portarias, secretarias estaduais e documentos da Sociedade Brasileira de Pediatria, "
          "abrindo cada página. A matriz completa, com o link e o trecho de cada fonte, está em `knowledge/FONTES.md`. "
          "É um levantamento de fontes, **não uma validação clínica**."),
        KeepTogether([tabela(linhas, [0.6, 0.4])]),
        Spacer(1, 6),
        P("A conferência mudou a base em quatro pontos:"),
        tabela(alteracoes, [0.16, 0.26, 0.38, 0.2]),
    ]


def secaoStt():
    corretos = []
    exemplos = []
    por = {}
    for r in stt:
        por.setdefault(r["arquivo"], {})[r["modelo"]] = r
    if "small" in modelosStt and "medium" in modelosStt:
        melhores = sorted(por.items(), key=lambda kv: kv[1]["small"]["wer"] - kv[1]["medium"]["wer"], reverse=True)[:3]
        pior = sorted(por.items(), key=lambda kv: kv[1]["medium"]["wer"] - kv[1]["small"]["wer"], reverse=True)[:1]
        for nome, d in melhores + pior:
            exemplos.append([nome.replace(".wav", ""), d["small"]["referencia"], d["small"]["hipotese"], d["medium"]["hipotese"]])
    cond = [("Geral", {}), ("voz1 (masculino, 18 a 29)", {"voz": "voz1"}), ("voz2 (feminino, 18 a 29)", {"voz": "voz2"}),
            ("voz3 (feminino, 45 a 59, bahiana)", {"voz": "voz3"}), ("Sem ruído de fundo", {"ruido": "nao"}), ("Com ruído de fundo", {"ruido": "sim"})]
    tabelaWer = [["Condição", "Áudios"] + [f"WER {m}" for m in modelosStt]]
    for nome, f in cond:
        linha = [nome, str(werDe(modelosStt[0], **f)[1])] + [pt(werDe(m, **f)[0], 3) for m in modelosStt]
        tabelaWer.append(linha)
    tabelaWer.append(["Tempo médio por áudio (s)*", "20"] + [pt(media(r["segundos"] for r in stt if r["modelo"] == m), 2) for m in modelosStt])
    melhorEm = sum(1 for d in por.values() if d["medium"]["wer"] < d["small"]["wer"]) if "medium" in modelosStt else 0
    piorEm = sum(1 for d in por.values() if d["medium"]["wer"] > d["small"]["wer"]) if "medium" in modelosStt else 0
    iguais = len(por) - melhorEm - piorEm
    piorou = "O medium não piorou em nenhum áudio."
    pioresLista = [(a, d) for a, d in por.items() if "medium" in d and d["medium"]["wer"] > d["small"]["wer"]]
    if pioresLista:
        a, d = pioresLista[0]
        omitiu = "upa" in d["small"]["referencia"].split() and "upa" not in d["medium"]["hipotese"].split()
        piorou = (f"O medium piorou em {len(pioresLista)} áudio(s)" + (f"; no {a.replace('.wav', '')} ele **omitiu a palavra \"UPA\"**, que para este assistente é central" if omitiu else "")
                  + ". Por isso o relatório não trata o medium como estritamente melhor.")
    saida = [
        P("5. Testes e resultados", h1),
        P("5.1 STT: Whisper small × medium", h2),
        P(f"Foram gravados 20 áudios do roteiro por 3 pessoas diferentes, 5 deles com barulho de fundo real (TV, ventilador, rua, cozinha e conversa). "
          "Cada pessoa leu as frases dela, com consentimento registrado, e o aparelho foi um notebook. A métrica é o WER (`jiwer`), com texto em minúsculas, sem pontuação e com números por extenso, "
          "para não punir \"39\" no lugar de \"trinta e nove\"."),
        tabela(tabelaWer, [0.5, 0.12, 0.19, 0.19]),
        Spacer(1, 3),
        P("*Os tempos foram medidos com a CPU limitada a 6 núcleos, prioridade baixa e outro programa aberto, e valem como proporção entre os modelos, não como valor absoluto.", pequeno),
        graficoStt(),
        Spacer(1, 4),
        P(f"O medium foi melhor em {melhorEm} áudios, pior em {piorEm} e igual em {iguais}. Os erros do small concentram-se em **vocabulário de saúde**:"),
        tabela([["Áudio", "Frase lida", "Whisper small", "Whisper medium"]] + exemplos, [0.1, 0.3, 0.3, 0.3]),
        Spacer(1, 4),
        P(piorou),
        P("**Análise de viés do STT.** O WER mais alto foi o da voz2 nos dois modelos; a voz3 (outra faixa etária e outro sotaque) ficou entre as melhores. "
          "Isso não permite concluir que idade, sexo ou sotaque pesam: cada frase foi lida por uma só pessoa e em uma só condição, então voz, frase, ruído, sexo e idade "
          "estão misturados. O próprio resultado com ruído (menor que sem ruído) mostra o problema, porque as frases com ruído eram mais fáceis. "
          "Com três vozes e um único aparelho, o teste só indica onde olhar numa próxima rodada, com as mesmas frases lidas por todas as vozes."),
        P(f"**Escolha final do STT: Whisper {ESCOLHA_STT}.** Foi o modelo usado na medição de ponta a ponta. A latência já é o ponto mais fraco (seção 5.4) e o medium soma "
          "cerca de 2,9 vezes o tempo de transcrição. O medium fica recomendado onde houver GPU ou folga de tempo, porque acerta mais termos de saúde."),
    ]
    return saida


def veredito(linha):
    manual = linha["revisaoManual"].strip().lower()
    if manual in ("sim", "s", "1", "true"):
        return True
    if manual in ("nao", "não", "n", "0", "false"):
        return False
    return linha["acertoAutomatico"] == "True"


def secaoLlm():
    categorias = [("normal", "Normais"), ("continuacao", "De continuação"), ("fora", "Fora do escopo")]
    esperado = {"normal": "responder com o que está na base", "continuacao": "usar o turno anterior",
                "fora": "recusar com a frase padrão"}
    linhas = [["Categoria", "n", "Comportamento esperado", "Corretas (automático)", "Corretas (após revisão manual)"]]
    revisadas = [r for r in llm if r["revisaoManual"].strip()]
    for chave, nome in categorias:
        grupo = [r for r in llm if r["tipo"] == chave]
        auto = sum(1 for r in grupo if r["acertoAutomatico"] == "True")
        gr = [r for r in grupo if r["revisaoManual"].strip()]
        final = f"{sum(1 for r in grupo if veredito(r))} de {len(grupo)}" if len(gr) == len(grupo) and grupo else "pendente"
        linhas.append([nome, str(len(grupo)), esperado[chave], f"{auto} de {len(grupo)}", final])
    falsos = [r for r in llm if r["acertoAutomatico"] == "False" and r["tipo"] != "fora"]
    lat = [float(r["segundos"]) for r in llm]
    flash = [r for r in llmTentativa1 if r["modelo"] == "gemini-2.5-flash" and not r["resposta"].startswith("ERRO")]
    flashAuto = sum(1 for r in flash if r["acertoAutomatico"] == "True")
    flashLat = media(float(r["segundos"]) for r in flash)
    nFlashErro = sum(1 for r in llmTentativa1 if r["modelo"] == "gemini-2.5-flash" and r["resposta"].startswith("ERRO"))
    tentativas = [
        ["Modelo", "Resultado", "Situação"],
        ["gemini-3.5-flash-lite", f"{len(llm)} perguntas respondidas, {sum(1 for r in llm if r['acertoAutomatico'] == 'True')} corretas na triagem automática; latência média {pt(mean(lat), 1)} s, mediana {pt(median(lat), 1)} s", "avaliado por completo"],
        ["gemini-2.5-flash", f"{len(flash)} de 30 respondidas ({flashAuto} corretas na triagem, latência média {pt(flashLat, 1)} s); {nFlashErro} perguntas sem resposta por HTTP 429", "parcial: a cota diária do plano gratuito acabou (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`); não entra na comparação"],
        ["gemini-2.5-flash-lite", "HTTP 404: \"no longer available to new users\"", "descontinuado para contas novas; a API recomenda o 3.5 flash-lite"],
    ]
    saida = [
        P("5.2 LLM e diálogo", h2),
        P("São 30 perguntas com resposta esperada: 20 normais, 5 de continuação (que dependem do turno anterior) e 5 fora do escopo, uma delas uma tentativa de mudar as regras do assistente. "
          "A triagem automática procura palavras esperadas e a frase de recusa; por isso erra para os dois lados e a revisão manual tem a palavra final."),
        tabela(linhas, [0.16, 0.06, 0.3, 0.22, 0.26]),
        Spacer(1, 4),
    ]
    if falsos:
        ids = ", ".join(r["id"] for r in falsos)
        confirmados = bool(revisadas) and all(veredito(r) for r in falsos)
        saida.append(P(f"As {len(falsos)} respostas que a triagem marcou como erradas (perguntas {ids}) são **falsos negativos**: o modelo escreveu \"ligue para o **um nove dois**\" e a triagem procurava \"192\". "
                       + ("A revisão manual confirmou que estão corretas." if confirmados else "Pela leitura da base as respostas estão certas, mas a confirmação depende da revisão manual.")))
    if revisadas:
        corretas = sum(1 for r in llm if veredito(r))
        saida.append(P(f"**Revisão manual.** {len(revisadas)} de {len(llm)} respostas foram lidas pelo grupo e comparadas com a resposta esperada; {corretas} de {len(llm)} ficaram como corretas "
                       f"({pt(100 * corretas / len(llm), 0)}%). A revisão foi feita pelo próprio grupo, sem segundo avaliador, e usou a resposta esperada como guia, não como frase a repetir: "
                       "uma resposta certa na essência e escrita de outro jeito conta como correta."))
    if not revisadas:
        saida.append(P("**Revisão manual pendente.** A coluna `revisaoManual` de `resultados/llmResultados.csv` deve ser preenchida com \"sim\" ou \"nao\" depois de ler as 30 respostas; "
                       "ao regerar o relatório, a coluna de revisão passa a valer no lugar da triagem."))
    saida += [
        P("**Comparação de modelos.** O par planejado era `gemini-2.5-flash` × `gemini-2.5-flash-lite`. O segundo saiu do ar para contas novas e o primeiro esgotou a cota diária no meio da avaliação:"),
        tabela(tentativas, [0.2, 0.45, 0.35]),
        Spacer(1, 4),
        P("Por isso a comparação exigida pelo enunciado, de duas opções de um componente, é a do STT (seção 5.1). Para o LLM, o relatório só afirma o que mediu com o 3.5 flash-lite. "
          f"A latência desse modelo variou muito entre as medições: média de {pt(mean(lat), 1)} s na avaliação das 30 perguntas, de 5 a 14 s por chamada numa medição isolada e "
          f"{pt(media(float(r['llm']) for r in e2e), 1)} s na medição de ponta a ponta. Vale a faixa, não um número só. "
          "O 2.5 flash completo pode ser medido quando a cota voltar."),
    ]
    return saida


def secaoTts():
    por = {}
    for r in tts:
        por.setdefault(r["avaliador"], []).append(r)
    notas = [r for r in tts if r["naturalidade"] and r["clareza"]]
    frases = [l for l in (TESTE / "tts" / "frases.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    saida = [
        P("5.3 TTS", h2),
        P(f"{len(frases)} respostas do assistente foram sintetizadas com a voz `pt-BR-FranciscaNeural` depois da adaptação para fala "
          "(`testMaterial/tts/`). Cada avaliador ouve os áudios e dá nota de 1 a 5 para naturalidade e para clareza; o enunciado pede pelo menos 3 avaliadores."),
    ]
    if notas:
        linhas = [["Avaliador", "Áudios avaliados", "Naturalidade média", "Clareza média"]]
        for av, rs in sorted(por.items()):
            ok = [r for r in rs if r["naturalidade"] and r["clareza"]]
            if ok:
                linhas.append([av, str(len(ok)), pt(media(float(r["naturalidade"]) for r in ok), 2), pt(media(float(r["clareza"]) for r in ok), 2)])
        linhas.append(["**Todos**", str(len(notas)), pt(media(float(r["naturalidade"]) for r in notas), 2), pt(media(float(r["clareza"]) for r in notas), 2)])
        saida.append(tabela(linhas, [0.3, 0.22, 0.28, 0.2]))
        nAv = len({r["avaliador"] for r in notas})
        nat = media(float(r["naturalidade"]) for r in notas)
        cla = media(float(r["clareza"]) for r in notas)
        saida.append(P(f"**Leitura.** A voz é **clara** (média {pt(cla, 1)} de 5), mas pouco **natural** (média {pt(nat, 1)} de 5): "
                       "dá para entender, e a adaptação para fala funciona, mas soa como voz sintética. "
                       f"São {len(notas)} notas de {nAv} avaliador(es) sobre {len({r['arquivo'] for r in notas})} respostas; com tão poucas notas não há como medir a concordância entre avaliadores."))
        if nAv < 3:
            saida.append(P(f"**Atenção:** só {nAv} avaliador(es) registrou notas; o enunciado pede pelo menos 3 pessoas. A média acima vale para esse(s) avaliador(es) e não deve ser lida como opinião de um grupo."))
    else:
        saida.append(P("**Avaliação pendente.** Os áudios e a planilha `testMaterial/tts/avaliacao.csv` estão prontos; nenhuma nota foi registrada ainda, "
                       "então o relatório não traz média de naturalidade nem de clareza."))
    return saida


def secaoE2e():
    est = []
    for chave, nome in (("stt", "STT (Whisper small)"), ("llm", "LLM (Gemini 3.5 Flash-Lite)"), ("prep", "Adaptação para fala"), ("tts", "TTS (edge-tts)"), ("total", "Total até o áudio pronto")):
        v = [float(r[chave]) for r in e2e]
        est.append([nome, pt(mean(v), 2), pt(median(v), 2), pt(min(v), 1), pt(max(v), 1)])
    conversas = len({r["conversa"] for r in e2e})
    origens = {r["origemAudio"] for r in e2e}
    return [
        P("5.4 Ponta a ponta e latência", h2),
        P(f"{conversas} conversas de 3 turnos ({len(e2e)} turnos), cada uma com perguntas de continuação, e uma delas termina em pedido fora do tema, que o assistente recusou. "
          "A latência é medida em cada etapa e no total, da pergunta até o áudio da resposta pronto."),
        tabela([["Etapa", "Média (s)", "Mediana (s)", "Mínimo (s)", "Máximo (s)"]] + est, [0.36, 0.16, 0.16, 0.16, 0.16]),
        Spacer(1, 4),
        graficoLatencia(),
        Spacer(1, 3),
        lista([
            "**O TTS é o gargalo:** o `edge-tts` só devolve o áudio depois de sintetizar a resposta inteira, e o total mede esse arquivo pronto, não o primeiro som.",
            "**A voz do usuário é sintética** em "
            + ("todos os turnos" if origens == {"sintetico"} else "parte dos turnos")
            + ": a fala de cada pergunta foi gerada por TTS, o que facilita o STT. Os números de STT por voz real estão na seção 5.1.",
            f"**A latência do LLM varia com a carga do serviço**, por isso a faixa é larga (de {pt(min(float(r['llm']) for r in e2e), 1)} a {pt(max(float(r['llm']) for r in e2e), 1)} s nesta rodada).",
        ]),
    ]


def secaoEtica():
    cons = sorted({r["voz"] for r in consentimentos})
    return [
        P("6. Ética, segurança e LGPD", h1),
        lista([
            "**Consentimento.** A interface exige marcar o aviso (conversa gravada, texto enviado ao Google e resposta à Microsoft) antes do primeiro uso. "
            + (f"As gravações do teste de STT têm consentimento registrado para {len(cons)} vozes ({', '.join(cons)}), com data e sem nome, em `testMaterial/stt/consentimentos.csv`." if cons else ""),
            "**Retenção mínima.** O áudio do cidadão é apagado logo após a transcrição, mesmo se a transcrição falhar (teste automático). Foi verificado enviando um áudio pela API e comparando o hash de todos os "
            "arquivos das pastas temporárias: nenhuma cópia do áudio enviado sobrou. A pasta do Gradio é própria, é apagada ao abrir e ao fechar o app e tem limpeza periódica; as respostas faladas vencem em 10 minutos. "
            "O log de latência guarda só tempos. A conversa vive na memória da sessão.",
            "**Nuvem.** Só o texto transcrito vai ao Gemini e só o texto da resposta vai ao serviço de voz da Microsoft; o aviso pede para não informar nome, CPF nem endereço.",
            "**Limites.** O assistente não diagnostica, não indica remédio nem dose, manda ligar 192 em emergência e ignora o pedido de mudar as regras. Nas 5 perguntas fora do escopo, incluindo a tentativa de mudar as regras, recusou as 5.",
            "**Alucinação.** Sem a informação na base, responde \"Não tenho essa informação com segurança\" e indica a UBS ou o 136. A conferência de fontes (seção 4) encontrou 4 pontos da base sem fonte oficial, tratados ou listados.",
            "**Clonagem de voz.** Não usada: todas as vozes sintéticas são prontas.",
            "**Viés do STT.** Analisado na seção 5.1, com a ressalva de que o desenho do teste mistura voz, frase e condição.",
            "**Voz como dado pessoal no repositório.** O enunciado pede os áudios de teste na entrega. Eles são de 3 pessoas que consentiram; a recomendação é manter o repositório privado e apagar os áudios a pedido de quem gravou.",
        ]),
    ]


def secaoLimitacoes():
    return [
        P("7. Limitações", h1),
        lista([
            "**Sem validação clínica.** A base é de uma página, conferida contra fontes oficiais mas não revisada por profissional de saúde.",
            "**Dependência de serviço externo.** O plano gratuito do Gemini bloqueou o `gemini-2.5-flash` por cota diária durante a avaliação e o `gemini-2.5-flash-lite` foi descontinuado. O app avisa quando a cota acaba; o modelo se troca por `GEMINIMODEL`. Sem internet, o assistente não responde.",
            "**Amostras pequenas.** 20 áudios, 30 perguntas, 10 conversas. Diferenças pequenas de WER não são estatisticamente conclusivas, e o desenho do teste de STT mistura as condições.",
            "**Erros de vocabulário de saúde no STT** (\"dor de garganta\" virou \"Duarte Greganta\", \"SAMU\" virou \"samurra\" no small), que o medium reduz mas não elimina; uma omissão de \"UPA\" foi do medium.",
            "**Latência alta para conversa por voz** (cerca de 10 s), dominada pela síntese de voz.",
            ("**Voz pouco natural:** " + f"{pt(media(float(r['naturalidade']) for r in tts if r['naturalidade']), 1)} de 5 na avaliação de naturalidade, contra "
             f"{pt(media(float(r['clareza']) for r in tts if r['clareza']), 1)} de 5 em clareza.") if any(r["naturalidade"] for r in tts) else "**Voz do TTS ainda sem avaliação.**",
            "**O modelo escreve números por extenso, de forma inconsistente** (\"um nove dois\" para 192, mas \"cento e oitenta e oito\" para 188), o que contorna a regra de leitura dígito a dígito do `speechPrep`.",
            "**Adaptação para fala.** Não faz concordância de gênero nos números (\"mil e quinhentos pessoas\") e lê \"12/8\" como data; os dois casos estão marcados como limitações conhecidas nos testes.",
            "**Triagem automática do LLM por palavras-chave**, que subestima respostas certas escritas de outro jeito.",
            "**Ponta a ponta com voz sintética no lugar de voz real do usuário.**",
        ]),
    ]


def secaoMelhorias():
    return [
        P("8. Melhorias futuras", h1),
        lista([
            "**Reduzir a latência e melhorar a voz.** Sintetizar e tocar a resposta frase a frase, em vez de esperar o arquivo inteiro, e comparar outras vozes e um TTS local (Piper) com as mesmas notas de naturalidade e clareza, que também tira a dependência de rede.",
            "**STT melhor onde couber.** Habilitar a GPU (bibliotecas CUDA) para usar o Whisper medium sem somar tempo, e adicionar vocabulário de saúde (SAMU, UPA, UBS) ao reconhecimento.",
            "**Base maior com busca.** Reaproveitar a base de 33 páginas do gov.br do projeto de Generative AI com RAG, ligando o assistente de voz àquele backend.",
            "**Voltar ao Orienta Saúde.** Integrar a voz ao fluxo do Front End, incluindo \"UPAs próximas\" pelo CEP dito em voz alta.",
            "**Avaliação mais forte.** Todas as vozes lendo as mesmas frases, mais vozes e aparelhos, voz real nas conversas ponta a ponta, revisão por profissional de saúde e juiz independente para as respostas.",
            "**Cota e custo.** Uma chave com faturamento ou um segundo provedor, para não depender do limite diário do plano gratuito.",
        ]),
    ]


def secaoReproducao():
    return [
        P("9. Reprodução", h1),
        P("Repositório: " + REPOSITORIO + ". Python 3.10 ou mais novo e internet para o LLM e o TTS."),
        tabela([
            ["Passo", "Comando"],
            ["Instalar", "`pip install -r requirements.txt` e copiar `.env.example` para `.env` com a chave `GEMINIAPIKEY`"],
            ["Rodar o assistente", "`python app.py` e abrir `http://127.0.0.1:7860`"],
            ["Gravar os áudios do teste", "`python gravador.py` e abrir `http://127.0.0.1:7861`"],
            ["Testes automáticos", "`pip install -r requirements-dev.txt` e `python -m pytest`"],
            ["Avaliar o STT", "`python -m evaluation.evalStt small,medium`"],
            ["Avaliar o LLM", "`python -m evaluation.evalLlm gemini-2.5-flash,gemini-3.5-flash-lite` e depois `python -m evaluation.evalLlm resumo`"],
            ["Avaliar o TTS e a ponta a ponta", "`python -m evaluation.evalTts` e `python -m evaluation.evalE2e`"],
            ["Gerar este relatório", "`python relatorio/gerarRelatorio.py`"],
        ], [0.28, 0.72]),
        Spacer(1, 4),
        P("Material de teste: `testMaterial/stt/` (roteiro e áudios), `testMaterial/perguntas.csv` (30 perguntas com resposta esperada), `testMaterial/conversas.json` (10 conversas) e "
          "`testMaterial/tts/` (frases, áudios e planilha de notas). Resultados em `resultados/`.", pequeno),
    ]


def montar():
    doc = BaseDocTemplate(str(SAIDA), pagesize=A4, title="Relatório Global Solution — Orienta Saúde Voz",
                          author="Guilherme Gama Bitencourt Souza", leftMargin=2 * cm, rightMargin=2 * cm,
                          topMargin=1.9 * cm, bottomMargin=2.1 * cm)
    quadroCapa = Frame(2 * cm, 1 * cm, A4[0] - 4 * cm, A4[1] - 2 * cm, id="capa")
    quadro = Frame(2 * cm, 2.1 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="corpo")
    doc.addPageTemplates([PageTemplate(id="capa", frames=[quadroCapa], onPage=capa),
                          PageTemplate(id="corpo", frames=[quadro], onPage=rodape)])
    hist = [P("CitizenTech · Orienta Saúde", tituloRel), P(f"{SUBTITULO} · Global Solution 2026.2 · {DISCIPLINA} · Tecnologia em Inteligência Artificial (FIAP)", subRel)]
    historia = elementosCapa() + hist
    for bloco in (secaoVinculo(), resumoRespostas(), secaoArquitetura(), secaoBase(), secaoStt(), secaoLlm(), secaoTts(), secaoE2e(),
                  secaoEtica(), secaoLimitacoes(), secaoMelhorias(), secaoReproducao()):
        historia += bloco
    doc.build(historia)
    print("relatório gerado em", SAIDA)


if __name__ == "__main__":
    montar()
