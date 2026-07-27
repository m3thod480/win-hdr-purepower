"""Análisis numérico de curvas tonales HDR."""

from dataclasses import dataclass

from hdrfix.curves import (
    colorcontrol_pure_power_sample,
    nits_to_pq,
    pq_to_nits,
    smooth_anchored_power_sample,
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