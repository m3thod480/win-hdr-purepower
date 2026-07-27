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


@dataclass(frozen=True)
class ToneCurveComparison:
    """Comparison of the tone-curve summaries for two profiles."""

    left: ToneCurveSummary
    right: ToneCurveSummary
    same_min_luminance: bool | None
    same_max_luminance: bool | None
    same_lut_entry_count: bool | None
    same_identity_status: bool | None


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


def compare_profiles(
    left: ICCProfile,
    right: ICCProfile,
) -> ToneCurveComparison:
    """Compare the MHC2 tone-curve data of two parsed profiles."""
    left_summary = summarize_tone_curve(left)
    right_summary = summarize_tone_curve(right)

    if not left_summary.has_mhc2 or not right_summary.has_mhc2:
        return ToneCurveComparison(
            left=left_summary,
            right=right_summary,
            same_min_luminance=None,
            same_max_luminance=None,
            same_lut_entry_count=None,
            same_identity_status=None,
        )

    assert left_summary.min_luminance is not None
    assert right_summary.min_luminance is not None
    assert left_summary.max_luminance is not None
    assert right_summary.max_luminance is not None

    return ToneCurveComparison(
        left=left_summary,
        right=right_summary,
        same_min_luminance=(
            abs(left_summary.min_luminance - right_summary.min_luminance)
            <= S15_FIXED_16_TOLERANCE
        ),
        same_max_luminance=(
            abs(left_summary.max_luminance - right_summary.max_luminance)
            <= S15_FIXED_16_TOLERANCE
        ),
        same_lut_entry_count=(
            left_summary.lut_entry_count == right_summary.lut_entry_count
        ),
        same_identity_status=(
            left_summary.is_identity == right_summary.is_identity
        ),
    )
