import pytest

from speechPrep import prepararFala


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # emergência é lida dígito a dígito
        ("Ligue 192 agora.", "Ligue um nove dois agora."),
        ("Disque Saúde 136.", "Disque Saúde um três seis."),
        ("CVV 188", "cê vê vê um oito oito"),
        # markdown e emoji não podem chegar ao TTS
        ("Ligue **192** agora. 🚑 Fique calmo.", "Ligue um nove dois agora. Fique calmo."),
        ("- Beba água\n- Descanse\n1. Observe", "Beba água. Descanse. Observe"),
        # siglas
        ("Procure a UBS ou a UPA.", "Procure a u bê ésse ou a upa."),
        ("Pode ser AVC.", "Pode ser á vê cê."),
        # números, horas, datas, porcentagem, temperatura
        ("em até 2 dias", "em até dois dias"),
        ("às 14h", "às catorze horas"),
        ("às 14h30", "às catorze horas e trinta minutos"),
        ("39,5 °C", "trinta e nove vírgula cinco graus"),
        ("12% dos casos", "doze por cento dos casos"),
        ("Vacina: 15/03/2026.", "Vacina: quinze de março de dois mil e vinte e seis."),
        ("dia 1/5", "dia primeiro de maio"),
        # casos que estavam errados na primeira versão
        ("A UPA funciona 24/7.", "A upa funciona vinte e quatro horas, todos os dias."),
        ("R$ 1.250,50", "mil duzentos e cinquenta reais e cinquenta centavos"),
        ("R$ 1,05", "um real e cinco centavos"),
        ("R$ 3", "três reais"),
        ("500 mg", "quinhentos miligramas"),
        ("1 mg", "um miligrama"),
        ("2,5 ml", "dois vírgula cinco mililitros"),
        ("3x ao dia", "três vezes ao dia"),
        ("140/90 mmHg", "cento e quarenta por noventa milímetros de mercúrio"),
        ("pressão 140/90", "pressão cento e quarenta por noventa"),
        ("0800", "zero oito zero zero"),
        ("Querido(a), calma.", "Querido, calma."),
    ],
)
def testPrepararFala(entrada, esperado):
    assert prepararFala(entrada) == esperado


def testSemDigitosNemSimbolosNaSaida():
    texto = "Febre de 39,5 °C há 3 dias? Ligue 192 ou vá à UPA, R$ 10, 500 mg, 12/04, 24/7, 14h30, 20%."
    saida = prepararFala(texto)
    assert not any(c.isdigit() for c in saida), saida
    for simbolo in ("%", "°", "R$", "*", "#", "/"):
        assert simbolo not in saida, (simbolo, saida)


def testSemVirgulaNoMeioDoNumero():
    # o num2words devolve "mil, duzentos"; a vírgula viraria pausa no meio do número falado
    assert "," not in prepararFala("1.250")


@pytest.mark.xfail(reason="limitação conhecida: o num2words não faz concordância de gênero (mil e quinhentas pessoas)")
def testConcordanciaDeGenero():
    assert prepararFala("1.500 pessoas") == "mil e quinhentas pessoas"


@pytest.mark.xfail(reason="limitação conhecida: 12/8 é lido como data (doze de agosto); só 3 dígitos ou mmHg viram pressão")
def testPressaoComDoisDigitos():
    assert prepararFala("pressão 12/8") == "pressão doze por oito"


def testTextoVazio():
    assert prepararFala("") == ""
