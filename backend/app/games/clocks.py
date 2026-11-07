from __future__ import annotations

from typing import Any

# A remaining clock at or below this many seconds counts as playing under
# time pressure (used by the interesting-score time-pressure bonus).
TIME_PRESSURE_THRESHOLD_SECONDS = 10


def extract_clock_metrics(raw_payload: dict[str, Any] | None, user_color: str | None) -> tuple[int | None, int | None]:
    """Return (user_lowest_clock_seconds, moves_under_time_pressure).

    Reads the Lichess payload `clocks` array, which holds the remaining
    centiseconds after each ply and aligns with the SAN move list
    (index 0 = white's first move).
    """
    if not isinstance(raw_payload, dict) or user_color not in {"white", "black"}:
        return None, None
    clocks = raw_payload.get("clocks")
    if not isinstance(clocks, list) or not clocks:
        return None, None

    user_offset = 0 if user_color == "white" else 1
    user_clocks = [
        float(clock)
        for index, clock in enumerate(clocks)
        if index % 2 == user_offset and isinstance(clock, (int, float))
    ]
    if not user_clocks:
        return None, None

    lowest_seconds = max(0, int(min(user_clocks) // 100))
    under_pressure = sum(1 for clock in user_clocks if clock <= TIME_PRESSURE_THRESHOLD_SECONDS * 100)
    return lowest_seconds, under_pressure
