"""Análisis numérico de la curva tonal final."""

from collections.abc import Iterable
from dataclasses import dataclass

from hdrfix.curves import (
    PURE_POWER_GAMMA,
    colorcontrol_pure_power_sample,
    generate_colorcontrol_lut,
    generate_shadow_stretch_lut,
    nits_to_pq,
    pq_to_nits,
    quantize_s15_fixed_16,
    shadow_stretch_power_sample,
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
    """Resultado de Pure Power y la curva final para una luminancia."""

    input_nits: float
    pure_power_nits: float
    shadow_stretch_nits: float

    @property
    def pure_power_delta_nits(self) -> float:
        """Cambio de Pure Power respecto a identidad."""
        return self.pure_power_nits - self.input_nits

    @property
    def shadow_stretch_delta_nits(self) -> float:
        """Cambio de Shadow Stretch respecto a identidad."""
        return self.shadow_stretch_nits - self.input_nits

    @property
    def shadow_stretch_minus_pure_power_nits(self) -> float:
        """Diferencia firmada: Shadow Stretch menos Pure Power."""
        return self.shadow_stretch_nits - self.pure_power_nits


@dataclass(frozen=True)
class CurveAnalysis:
    """Resumen de la curva final frente a Pure Power."""

    entries: int
    samples: tuple[CurveSample, ...]
    quantized_different_entries: int
    max_difference_nits: float
    max_difference_input_nits: float


def analyze_curve_sample(
    input_nits: float,
    *,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> CurveSample:
    """Compara Pure Power y la curva final en una luminancia."""

    input_pq = nits_to_pq(input_nits)
    pure_power_pq = colorcontrol_pure_power_sample(
        input_pq,
        gamma=PURE_POWER_GAMMA,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )
    shadow_stretch_pq = shadow_stretch_power_sample(
        input_pq,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )

    return CurveSample(
        input_nits=input_nits,
        pure_power_nits=pq_to_nits(pure_power_pq),
        shadow_stretch_nits=pq_to_nits(shadow_stretch_pq),
    )


def sample_curves(
    luminances: Iterable[float] = DEFAULT_SAMPLE_LUMINANCES,
    *,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
) -> tuple[CurveSample, ...]:
    """Analiza las dos curvas en varias luminancias."""

    return tuple(
        analyze_curve_sample(
            luminance,
            sdr_white_nits=sdr_white_nits,
            sdr_black_nits=sdr_black_nits,
        )
        for luminance in luminances
    )


def analyze_curves(
    *,
    entries: int = 1024,
    sdr_white_nits: float = 100.0,
    sdr_black_nits: float = 0.0,
    sample_luminances: Iterable[float] = DEFAULT_SAMPLE_LUMINANCES,
) -> CurveAnalysis:
    """Compara la LUT final con su base Pure Power."""

    pure_power_lut = generate_colorcontrol_lut(
        entries=entries,
        gamma=PURE_POWER_GAMMA,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )
    shadow_stretch_lut = generate_shadow_stretch_lut(
        entries=entries,
        sdr_white_nits=sdr_white_nits,
        sdr_black_nits=sdr_black_nits,
    )
    (
        quantized_different_entries,
        max_difference_nits,
        max_difference_input_nits,
    ) = _compare_luts(pure_power_lut, shadow_stretch_lut)

    return CurveAnalysis(
        entries=entries,
        samples=sample_curves(
            sample_luminances,
            sdr_white_nits=sdr_white_nits,
            sdr_black_nits=sdr_black_nits,
        ),
        quantized_different_entries=quantized_different_entries,
        max_difference_nits=max_difference_nits,
        max_difference_input_nits=max_difference_input_nits,
    )


def _compare_luts(
    pure_power_lut: tuple[float, ...],
    shadow_stretch_lut: tuple[float, ...],
) -> tuple[int, float, float]:
    different_entries = 0
    max_difference_nits = 0.0
    max_difference_input_nits = 0.0

    for index, (pure_power_pq, shadow_stretch_pq) in enumerate(
        zip(pure_power_lut, shadow_stretch_lut, strict=True)
    ):
        if quantize_s15_fixed_16(
            pure_power_pq
        ) != quantize_s15_fixed_16(shadow_stretch_pq):
            different_entries += 1

        difference_nits = abs(
            pq_to_nits(shadow_stretch_pq)
            - pq_to_nits(pure_power_pq)
        )
        if difference_nits > max_difference_nits:
            input_pq = index / (len(pure_power_lut) - 1)
            max_difference_nits = difference_nits
            max_difference_input_nits = pq_to_nits(input_pq)

    return (
        different_entries,
        max_difference_nits,
        max_difference_input_nits,
    )
