import re

from num2words import num2words

siglas = {
    "SUS": "sus",
    "UPA": "upa",
    "UBS": "u bê ésse",
    "UTI": "u tê í",
    "SAMU": "samu",
    "CVV": "cê vê vê",
    "AVC": "á vê cê",
    "CEP": "cép",
    "CPF": "cê pê efe",
}

numerosEmergencia = {"190", "192", "193", "188", "136", "199"}

meses = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# (singular, plural). Só entram unidades que não são ambíguas escritas sozinhas.
unidades = {
    "mcg": ("micrograma", "microgramas"),
    "mg": ("miligrama", "miligramas"),
    "ml": ("mililitro", "mililitros"),
    "kg": ("quilo", "quilos"),
    "km": ("quilômetro", "quilômetros"),
    "cm": ("centímetro", "centímetros"),
    "bpm": ("batimento por minuto", "batimentos por minuto"),
    "g": ("grama", "gramas"),
}

padraoEmoji = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U0000FE0F\U0000200D]+",
    flags=re.UNICODE,
)


def removerMarkdown(texto):
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"^\s*[-*•]\s+", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^\s*\d+[.)]\s+", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^#+\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"[*_`#>|~]+", "", texto)
    return texto


def removerMarcaDeGenero(texto):
    # "querido(a)", "obrigado(a)": o TTS lê a letra solta. Fica a forma sem a marca.
    return re.sub(r"(?<=\w)\((?:a|o|as|os|s)\)", "", texto)


def extenso(numero):
    # o num2words põe vírgula em "mil, duzentos"; no TTS isso vira uma pausa no meio do número
    return num2words(numero, lang="pt_BR").replace(",", "")


def porExtensoDigitos(digitos):
    return " ".join(extenso(int(digito)) for digito in digitos)


def converterDecimal(correspondencia):
    inteiro = int(correspondencia.group(1))
    decimal = correspondencia.group(2)
    parteDecimal = extenso(int(decimal)) if len(decimal) <= 2 else porExtensoDigitos(decimal)
    return f"{extenso(inteiro)} vírgula {parteDecimal}"


def converterNumero(correspondencia):
    texto = correspondencia.group(0)
    # telefone de emergência, e qualquer número com zero à esquerda (0800), é lido dígito a dígito
    if texto in numerosEmergencia or (len(texto) > 1 and texto.startswith("0")):
        return porExtensoDigitos(texto)
    return extenso(int(texto))


def converterData(correspondencia):
    dia = int(correspondencia.group(1))
    mes = int(correspondencia.group(2))
    ano = correspondencia.group(3)
    if not 1 <= mes <= 12 or not 1 <= dia <= 31:
        return correspondencia.group(0)
    diaExtenso = "primeiro" if dia == 1 else extenso(dia)
    partes = f"{diaExtenso} de {meses[mes - 1]}"
    if ano:
        anoCompleto = int(ano) + 2000 if len(ano) == 2 else int(ano)
        partes += f" de {extenso(anoCompleto)}"
    return partes


def converterMoeda(correspondencia):
    reais = int(correspondencia.group(1))
    centavos = correspondencia.group(2)
    texto = f"{extenso(reais)} {'real' if reais == 1 else 'reais'}"
    if centavos:
        valor = int(centavos.ljust(2, "0"))
        if valor:
            texto += f" e {extenso(valor)} {'centavo' if valor == 1 else 'centavos'}"
    return texto


def converterUnidade(correspondencia):
    numero = correspondencia.group(1)
    singular, plural = unidades[correspondencia.group(2).lower()]
    return f"{numero} {singular if numero == '1' else plural}"


def converterNumeros(texto):
    # "1.250" em português é mil duzentos e cinquenta: tira o ponto de milhar antes de tudo
    texto = re.sub(r"\b\d{1,3}(?:\.\d{3})+(?!\d)", lambda m: m.group(0).replace(".", ""), texto)
    texto = re.sub(r"\b24\s*/\s*7\b", "vinte e quatro horas, todos os dias", texto)
    texto = re.sub(r"R\$\s*(\d+)(?:,(\d{1,2}))?", converterMoeda, texto)
    texto = re.sub(r"\b(\d{1,3})\s*[x/]\s*(\d{1,3})\s*mmHg\b", r"\1 por \2 milímetros de mercúrio", texto, flags=re.IGNORECASE)
    # pressão sem unidade: 140/90 (3 dígitos na frente nunca é data); 12/8 continua sendo lido como data
    texto = re.sub(r"\b(\d{3})\s*[x/]\s*(\d{2,3})\b", r"\1 por \2", texto)
    texto = re.sub(r"\b(\d{1,2})h(\d{2})\b", r"\1 horas e \2 minutos", texto)
    texto = re.sub(r"\b(\d+(?:,\d+)?)\s*(mcg|mg|ml|kg|km|cm|bpm|g)\b", converterUnidade, texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(\d+)\s*x\b", r"\1 vezes", texto)
    texto = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", converterData, texto)
    texto = re.sub(r"(\d+)\s*h\b", r"\1 horas", texto)
    texto = re.sub(r"(\d+)\s*°\s*C\b", r"\1 graus", texto)
    texto = re.sub(r"(\d+)\s*%", r"\1 por cento", texto)
    texto = re.sub(r"\b(\d+),(\d+)\b", converterDecimal, texto)
    texto = re.sub(r"\b\d+\b", converterNumero, texto)
    return texto


def converterSiglas(texto):
    for sigla, leitura in siglas.items():
        texto = re.sub(rf"\b{sigla}\b", leitura, texto)
    return texto


def normalizarEspacos(texto):
    texto = re.sub(r"\s*\n+\s*", ". ", texto)
    texto = re.sub(r"\.\s*\.", ".", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"\s+([.,!?;:])", r"\1", texto)
    return texto.strip()


def prepararFala(texto):
    texto = padraoEmoji.sub("", texto)
    texto = removerMarkdown(texto)
    texto = removerMarcaDeGenero(texto)
    texto = converterNumeros(texto)
    texto = converterSiglas(texto)
    return normalizarEspacos(texto)
