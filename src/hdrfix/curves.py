"""Funciones matemáticas para construir curvas HDR Pure Power."""

PQ_M1 = 0.1593017578125
PQ_M2 = 78.84375
PQ_C1 = 0.8359375
PQ_C2 = 18.8515625
PQ_C3 = 18.6875
PQ_MAX_LUMINANCE = 10_000.0


def pq_to_nits(signal_value: float) -> float:
    """Convierte una señal PQ normalizada en luminancia absoluta."""
    if not 0.0 <= signal_value <= 1.0:
        raise ValueError("La señal PQ debe estar entre 0 y 1.")

    signal_power = signal_value ** (1.0 / PQ_M2)

    numerator = max(signal_power - PQ_C1, 0.0)
    denominator = PQ_C2 - PQ_C3 * signal_power

    return PQ_MAX_LUMINANCE * (
        numerator / denominator
    ) ** (1.0 / PQ_M1)


def nits_to_pq(luminance: float) -> float:
    """Convierte luminancia absoluta en una señal PQ normalizada."""
    if not 0.0 <= luminance <= PQ_MAX_LUMINANCE:
        raise ValueError(
            "La luminancia debe estar entre 0 y 10.000 nits."
        )

    normalized_luminance = luminance / PQ_MAX_LUMINANCE
    luminance_power = normalized_luminance**PQ_M1

    numerator = PQ_C1 + PQ_C2 * luminance_power
    denominator = 1.0 + PQ_C3 * luminance_power

    return (numerator / denominator) ** PQ_M2