from hdrfix.comparison import (
    compare_profiles,
    is_identity_lut,
    summarize_tone_curve,
)
from hdrfix.icc import ICCProfile, MHC2Tag


def test_two_entry_identity_lut():
    assert is_identity_lut((0.0, 1.0))


def test_four_entry_identity_lut():
    assert is_identity_lut((0.0, 1 / 3, 2 / 3, 1.0))


def test_non_identity_lut():
    assert not is_identity_lut((0.0, 0.20, 0.70, 1.0))


def test_identity_lut_requires_at_least_two_entries():
    assert not is_identity_lut(())
    assert not is_identity_lut((0.0,))

def make_profile(
    red_lut: tuple[float, ...],
    green_lut: tuple[float, ...] | None = None,
    blue_lut: tuple[float, ...] | None = None,
    *,
    min_luminance: float = 0.0,
    max_luminance: float = 520.0,
) -> ICCProfile:
    green_lut = red_lut if green_lut is None else green_lut
    blue_lut = red_lut if blue_lut is None else blue_lut

    mhc2 = MHC2Tag(
        lut_entry_count=len(red_lut),
        min_luminance=min_luminance,
        max_luminance=max_luminance,
        matrix_offset=36,
        red_lut_offset=84,
        green_lut_offset=100,
        blue_lut_offset=116,
        red_lut=red_lut,
        green_lut=green_lut,
        blue_lut=blue_lut,
    )

    return ICCProfile(
        file_size=840,
        signature="acsp",
        tags=(),
        mhc2=mhc2,
    )

def test_summarizes_identity_profile():
    profile = make_profile((0.0, 1.0))

    summary = summarize_tone_curve(profile)

    assert summary.has_mhc2
    assert summary.min_luminance == 0.0
    assert summary.max_luminance == 520.0
    assert summary.lut_entry_count == 2
    assert summary.rgb_channels_equal
    assert summary.is_identity


def test_summarizes_non_identity_profile():
    profile = make_profile((0.0, 0.20, 0.70, 1.0))

    summary = summarize_tone_curve(profile)

    assert summary.has_mhc2
    assert summary.lut_entry_count == 4
    assert summary.rgb_channels_equal
    assert not summary.is_identity


def test_detects_different_rgb_channels():
    profile = make_profile(
        red_lut=(0.0, 1.0),
        green_lut=(0.0, 0.8),
        blue_lut=(0.0, 1.0),
    )

    summary = summarize_tone_curve(profile)

    assert not summary.rgb_channels_equal
    assert not summary.is_identity


def test_summarizes_profile_without_mhc2():
    profile = ICCProfile(
        file_size=200,
        signature="acsp",
        tags=(),
        mhc2=None,
    )

    summary = summarize_tone_curve(profile)

    assert not summary.has_mhc2
    assert summary.min_luminance is None
    assert summary.max_luminance is None
    assert summary.lut_entry_count is None
    assert summary.rgb_channels_equal is None
    assert summary.is_identity is None


def test_compares_identity_and_corrected_profiles():
    windows_profile = make_profile((0.0, 1.0))

    corrected_profile = make_profile(
        (0.0, 0.20, 0.70, 1.0)
    )

    comparison = compare_profiles(
        windows_profile,
        corrected_profile,
    )

    assert comparison.left.lut_entry_count == 2
    assert comparison.left.is_identity is True

    assert comparison.right.lut_entry_count == 4
    assert comparison.right.is_identity is False

    assert comparison.same_min_luminance is True
    assert comparison.same_max_luminance is True
    assert comparison.same_lut_entry_count is False
    assert comparison.same_identity_status is False


def test_compares_equivalent_profiles_with_fixed_point_tolerance():
    tolerance = 1 / 65536
    left = make_profile(
        (0.0, 1.0),
        min_luminance=0.25,
        max_luminance=520.0,
    )
    right = make_profile(
        (0.0, 1.0),
        min_luminance=0.25 + tolerance,
        max_luminance=520.0 - tolerance,
    )

    comparison = compare_profiles(left, right)

    assert comparison.left == summarize_tone_curve(left)
    assert comparison.right == summarize_tone_curve(right)
    assert comparison.same_min_luminance is True
    assert comparison.same_max_luminance is True
    assert comparison.same_lut_entry_count is True
    assert comparison.same_identity_status is True


def test_comparison_fields_are_unknown_when_either_profile_has_no_mhc2():
    with_mhc2 = make_profile((0.0, 1.0))
    without_mhc2 = ICCProfile(
        file_size=200,
        signature="acsp",
        tags=(),
        mhc2=None,
    )

    comparison = compare_profiles(with_mhc2, without_mhc2)

    assert comparison.left.has_mhc2 is True
    assert comparison.right.has_mhc2 is False
    assert comparison.same_min_luminance is None
    assert comparison.same_max_luminance is None
    assert comparison.same_lut_entry_count is None
    assert comparison.same_identity_status is None
