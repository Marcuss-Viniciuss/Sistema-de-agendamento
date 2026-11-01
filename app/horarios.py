"""Calendário de funcionamento: dias úteis, horas e blocos de marcação.

Funções puras, sem base de dados nem HTTP, por isso são fáceis de testar.
Todas as marcações têm a duração de um bloco (30 min por defeito, ou 60 com
SLOT_MINUTOS=60). Como todos os blocos têm o mesmo tamanho e começam na
grelha, dois blocos ou são iguais ou não se sobrepõem.
"""

import os
from datetime import date, datetime, time, timedelta

ABERTURA = time(9, 0)
FECHO = time(18, 0)
PAUSA_INICIO = time(12, 0)
PAUSA_FIM = time(13, 0)


def duracao_slot() -> int:
    """Duração do bloco em minutos: 30 ou 60 (lido a cada chamada, como o caminho da BD)."""
    try:
        valor = int(os.getenv("SLOT_MINUTOS", "30"))
    except ValueError:
        return 30
    return valor if valor in (30, 60) else 30


def dia_util(dia: date) -> bool:
    return dia.weekday() < 5  # 0 = segunda ... 4 = sexta


def gerar_slots(dia: date) -> list[datetime]:
    """Todos os inícios de bloco possíveis nesse dia (vazio ao fim de semana)."""
    if not dia_util(dia):
        return []

    passo = timedelta(minutes=duracao_slot())
    fecho = datetime.combine(dia, FECHO)
    slots = []
    inicio = datetime.combine(dia, ABERTURA)

    while inicio + passo <= fecho:
        fim = inicio + passo
        # Um bloco que toque na pausa de almoço não pode ser marcado
        toca_no_almoco = inicio.time() < PAUSA_FIM and fim.time() > PAUSA_INICIO
        if not toca_no_almoco:
            slots.append(inicio)
        inicio = fim

    return slots


def descricao_expediente() -> str:
    return (
        f"segunda a sexta, das {ABERTURA:%H:%M} às {PAUSA_INICIO:%H:%M} "
        f"e das {PAUSA_FIM:%H:%M} às {FECHO:%H:%M}, em blocos de {duracao_slot()} minutos"
    )
