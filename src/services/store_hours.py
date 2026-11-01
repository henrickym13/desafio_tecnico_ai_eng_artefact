"""Horário de funcionamento (manual §2), calculado em Python: o LLM não sabe que horas são.

Os horários abaixo duplicam o §2 do PDF; `tests/unit/test_policies.py` garante que continuam
iguais ao manual. O manual não traz lista de feriados.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Campo_Grande")
HOURS: dict[int, tuple[time, time]] = {  # 0 = segunda ... 6 = domingo (fechado)
    0: (time(9, 0), time(18, 0)),
    1: (time(9, 0), time(18, 0)),
    2: (time(9, 0), time(18, 0)),
    3: (time(9, 0), time(18, 0)),
    4: (time(9, 0), time(18, 0)),
    5: (time(9, 0), time(13, 0)),
}
WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]


def _fmt(t: time) -> str:
    return t.strftime("%H:%M")


def store_status(now: datetime) -> dict:
    now = now.replace(tzinfo=TZ) if now.tzinfo is None else now.astimezone(TZ)
    hours = HOURS.get(now.weekday())
    is_open = bool(hours and hours[0] <= now.time() < hours[1])

    next_opening = None
    if not is_open:
        for offset in range(8):
            day = now.date() + timedelta(days=offset)
            h = HOURS.get(day.weekday())
            if h and (offset > 0 or now.time() < h[0]):
                next_opening = {"dia_semana": WEEKDAYS_PT[day.weekday()],
                                "data": day.isoformat(), "hora": _fmt(h[0])}
                break

    return {
        "aberta_agora": is_open,
        "agora": now.strftime("%Y-%m-%d %H:%M"),
        "dia_semana": WEEKDAYS_PT[now.weekday()],
        "horario_hoje": f"{_fmt(hours[0])} às {_fmt(hours[1])}" if hours else "Fechado",
        "proxima_abertura": next_opening,
        "aviso_feriados": "O manual informa que feriados são fechados, mas não traz a lista de feriados. "
                          "Se hoje for feriado, a loja está fechada.",
    }
