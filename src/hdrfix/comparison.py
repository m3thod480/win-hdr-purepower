"""Funciones de solo lectura para comparar perfiles HDR."""

from collections.abc import Sequence
from dataclasses import dataclass

from .icc import ICCProfile


S15_FIXED_16_TOLERANCE = 1 / 65536

@dataclass(frozen=True)
class ToneCurveSummary:
    """Resumen de la información tonal MHC2 de un perfil."""

    has_mhc2: bool
    min_luminance: float | None
    max_luminance: float | None
    lut_entry_count: int | None
    rgb_channels_equal: bool | None
    is_identity: bool | None

def is_identity_lut(
    values: Sequence[float],
    tolerance: float = S15_FIXED_16_TOLERANCE,
) -> bool:
    """Comprueba si una LUT deja todos sus valores sin modificar."""
    if len(values) < 2:
        return False

    last_index = len(values) - 1

    for index, actual_value in enumerate(values):
        expected_value = index / last_index

        if abs(actual_value - expected_value) > tolerance:
            return False

    return True

def summarize_tone_curve(profile: ICCProfile) -> ToneCurveSummary:
    """Extrae un resumen tonal de un perfil ICC ya analizado."""
    mhc2 = profile.mhc2

    if mhc2 is None:
        return ToneCurveSummary(
            has_mhc2=False,
            min_luminance=None,
            max_luminance=None,
            lut_entry_count=None,
            rgb_channels_equal=None,
            is_identity=None,
        )

    rgb_channels_equal = (
        mhc2.red_lut == mhc2.green_lut == mhc2.blue_lut
    )

    all_channels_are_identity = all(
        is_identity_lut(channel)
        for channel in (
            mhc2.red_lut,
            mhc2.green_lut,
            mhc2.blue_lut,
        )
    )

    return ToneCurveSummary(
        has_mhc2=True,
        min_luminance=mhc2.min_luminance,
        max_luminance=mhc2.max_luminance,
        lut_entry_count=mhc2.lut_entry_count,
        rgb_channels_equal=rgb_channels_equal,
        is_identity=all_channels_are_identity,
    )