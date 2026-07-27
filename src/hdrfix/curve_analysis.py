"""Análisis numérico de curvas tonales HDR."""

from collections.abc import Iterable
from dataclasses import dataclass

from hdrfix.curves import (
    colorcontrol_pure_power_sample,
    generate_colorcontrol_lut,
    generate_smooth_anchored_lut,
    nits_to_pq,
    pq_to_nits,
    quantize_s15_fixed_16,
    smooth_anchored_power_sample,
)

DEFAULT_SAMPLE_LUMINANCES = (
    0.1,
    1.0,
    5.0,
    10.0,
    25.0,
    50.0,
    75.0,
    100.0,
)

@dataclass(frozen=True)
class CurveSample:
    """Resultado de ambas curvas para una luminancia concreta."""

    input_nits: float
    colorcontrol_nits: float
    smooth_nits: float

    @property
    def colorcontrol_delta_nits(self) -> float:
        """Cambio de ColorControl respecto a identidad."""
        return self.colorcontrol_nits - self.input_nits

    @property
    def smooth_delta_nits(self) -> float:
        """Cambio de Smooth respecto a identidad."""
        return self.smooth_nits - self.input_nits

    @property
    def difference_nits(self) -> float:
        """Diferencia firmada: Smooth menos ColorControl."""
        return self.smooth_nits - self.colorcontrol_nits

    @property
    def colorcontrol_distance_from_identity_nits(self) -> float:
        return abs(self.colorcontrol_delta_nits)

    @property
    def smooth_distance_from_identity_nits(self) -> float:
        return abs(self.smooth_delta_nits)

@dataclass(frozen=True)
class CurveAnalysis:
    """Resumen de la comparación entre ambas LUT."""

    entries: int
    samples: tuple[CurveSample, ...]

    quantized_different_entries: int
    quantized_smooth_brighter_entries: int
    quantized_smooth_darker_entries: int
    quantized_equal_entries: int

    max_absolute_difference_nits: float
    max_signed_difference_nits: float
    max_difference_input_nits: float

def analyze_curve_sample(
    input_nits: float,
    *,
    gamma: float = 2.2,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> CurveSample:
    """Compara ambas transformaciones en una luminancia de entrada."""

    input_pq = nits_to_pq(input_nits)

    colorcontrol_pq = colorcontrol_pure_power_sample(
        input_pq,
        gamma=gamma,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )

    smooth_pq = smooth_anchored_power_sample(
        input_pq,
        gamma=gamma,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )

    return CurveSample(
        input_nits=input_nits,
        colorcontrol_nits=pq_to_nits(colorcontrol_pq),
        smooth_nits=pq_to_nits(smooth_pq),
    )

def sample_curves(
    luminances: Iterable[float] = DEFAULT_SAMPLE_LUMINANCES,
    *,
    gamma: float = 2.2,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> tuple[CurveSample, ...]:
    """Analiza ambas curvas en varias luminancias."""

    return tuple(
        analyze_curve_sample(
            luminance,
            gamma=gamma,
            sdr_white_nits=sdr_white_nits,
            sdr_black_nits=sdr_black_nits,
        )
        for luminance in luminances
    )

def analyze_curves(
    *,
    entries: int = 1024,
    gamma: float = 2.2,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
    sample_luminances: Iterable[float] = DEFAULT_SAMPLE_LUMINANCES,
) -> CurveAnalysis:
    """Compara las LUT completas de ColorControl y Smooth Anchored."""

    colorcontrol_lut = generate_colorcontrol_lut(
        entries=entries,
        gamma=gamma,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )

    smooth_lut = generate_smooth_anchored_lut(
        entries=entries,
        gamma=gamma,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )

    quantized_different_entries = 0
    quantized_smooth_brighter_entries = 0
    quantized_smooth_darker_entries = 0
    quantized_equal_entries = 0

    max_absolute_difference_nits = 0.0
    max_signed_difference_nits = 0.0
    max_difference_input_nits = 0.0

    for index, (colorcontrol_pq, smooth_pq) in enumerate(
        zip(colorcontrol_lut, smooth_lut, strict=True)
    ):
        colorcontrol_quantized = quantize_s15_fixed_16(
            colorcontrol_pq
        )
        smooth_quantized = quantize_s15_fixed_16(smooth_pq)

        if smooth_quantized > colorcontrol_quantized:
            quantized_smooth_brighter_entries += 1
            quantized_different_entries += 1
        elif smooth_quantized < colorcontrol_quantized:
            quantized_smooth_darker_entries += 1
            quantized_different_entries += 1
        else:
            quantized_equal_entries += 1

        input_pq = index / (entries - 1)
        input_nits = pq_to_nits(input_pq)

        colorcontrol_nits = pq_to_nits(colorcontrol_pq)
        smooth_nits = pq_to_nits(smooth_pq)

        signed_difference_nits = (
            smooth_nits - colorcontrol_nits
        )
        absolute_difference_nits = abs(
            signed_difference_nits
        )

        if (
            absolute_difference_nits
            > max_absolute_difference_nits
        ):
            max_absolute_difference_nits = (
                absolute_difference_nits
            )
            max_signed_difference_nits = (
                signed_difference_nits
            )
            max_difference_input_nits = input_nits

    return CurveAnalysis(
        entries=entries,
        samples=sample_curves(
            sample_luminances,
            gamma=gamma,
            sdr_white_nits=sdr_white_nits,
            sdr_black_nits=sdr_black_nits,
        ),
        quantized_different_entries=(
            quantized_different_entries
        ),
        quantized_smooth_brighter_entries=(
            quantized_smooth_brighter_entries
        ),
        quantized_smooth_darker_entries=(
            quantized_smooth_darker_entries
        ),
        quantized_equal_entries=quantized_equal_entries,
        max_absolute_difference_nits=(
            max_absolute_difference_nits
        ),
        max_signed_difference_nits=(
            max_signed_difference_nits
        ),
        max_difference_input_nits=(
            max_difference_input_nits
        ),
    )