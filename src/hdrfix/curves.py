"""Funciones matemáticas para construir curvas HDR Pure Power."""

PQ_M1 = 0.1593017578125
PQ_M2 = 78.84375
PQ_C1 = 0.8359375
PQ_C2 = 18.8515625
PQ_C3 = 18.6875
PQ_MAX_LUMINANCE = 10_000.0

SRGB_LINEAR_THRESHOLD = 0.00313066844250063
SRGB_LINEAR_SCALE = 12.92
SRGB_OFFSET = 0.055
SRGB_SCALE = 1.055
SRGB_ENCODING_GAMMA = 2.4


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

def luminance_to_srgb_signal(
    luminance: float,
    white_luminance: float,
    black_luminance: float = 0.0,
) -> float:
    """Normaliza una luminancia y la codifica con la curva piecewise sRGB."""
    if white_luminance <= black_luminance:
        raise ValueError(
            "La luminancia blanca debe ser mayor que la luminancia negra."
        )

    normalized = (
        luminance - black_luminance
    ) / (
        white_luminance - black_luminance
    )

    # Todo lo que quede fuera del rango SDR se limita a 0–1.
    normalized = max(0.0, min(1.0, normalized))

    if normalized <= SRGB_LINEAR_THRESHOLD:
        return normalized * SRGB_LINEAR_SCALE

    return (
        SRGB_SCALE
        * normalized ** (1.0 / SRGB_ENCODING_GAMMA)
        - SRGB_OFFSET
    )

def colorcontrol_pure_power_sample(
    input_pq: float,
    *,
    gamma: float = 2.2,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> float:
    """Calcula una salida de la curva Pure Power usada por ColorControl."""
    if gamma <= 0.0:
        raise ValueError("La gamma debe ser mayor que cero.")

    if not (
        0.0 <= sdr_black_nits
        < sdr_white_nits
        <= PQ_MAX_LUMINANCE
    ):
        raise ValueError(
            "El rango SDR debe estar entre 0 y 10.000 nits "
            "y el blanco debe superar al negro."
        )

    # 1. Convertimos la entrada PQ a luminancia física.
    original_nits = pq_to_nits(input_pq)

    # 2. Interpretamos esa luminancia mediante la curva piecewise sRGB.
    srgb_signal = luminance_to_srgb_signal(
        luminance=original_nits,
        white_luminance=sdr_white_nits,
        black_luminance=sdr_black_nits,
    )

    # 3. Aplicamos la potencia objetivo, por ejemplo 2.2.
    corrected_nits = (
        sdr_black_nits
        + (sdr_white_nits - sdr_black_nits)
        * srgb_signal**gamma
    )

    # 4. Volvemos a codificar la luminancia corregida como PQ.
    corrected_pq = nits_to_pq(max(0.0, corrected_nits))

    # 5. Reducimos linealmente la corrección conforme nos acercamos
    #    al blanco SDR. Al alcanzarlo, la salida vuelve a identidad.
    fade_to_identity = min(
        1.0,
        original_nits / sdr_white_nits,
    )

    return corrected_pq + fade_to_identity * (
        input_pq - corrected_pq
    )

def generate_colorcontrol_lut(
    *,
    entries: int = 1024,
    gamma: float = 2.2,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> tuple[float, ...]:
    """Genera una LUT Pure Power equivalente a la de ColorControl."""
    if entries < 2:
        raise ValueError("La LUT debe contener al menos dos entradas.")

    if entries > 4096:
        raise ValueError("MHC2 admite como máximo 4096 entradas.")

    last_index = entries - 1

    return tuple(
        colorcontrol_pure_power_sample(
            index / last_index,
            gamma=gamma,
            sdr_white_nits=sdr_white_nits,
            sdr_black_nits=sdr_black_nits,
        )
        for index in range(entries)
    )

S15_FIXED_16_SCALE = 65_536


def quantize_s15_fixed_16(value: float) -> int:
    """Convierte un float al entero utilizado por s15Fixed16."""
    return round(value * S15_FIXED_16_SCALE)