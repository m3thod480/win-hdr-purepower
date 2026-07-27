import pytest

from hdrfix.curve_analysis import (
    DEFAULT_SAMPLE_LUMINANCES,
    analyze_curve_sample,
    analyze_curves,
    sample_curves,
)

def test_smooth_darkens_near_black_more_than_colorcontrol():
    sample = analyze_curve_sample(1.0)

    assert sample.smooth_nits < sample.colorcontrol_nits
    assert sample.colorcontrol_nits < sample.input_nits
    assert sample.difference_nits < 0.0


def test_smooth_transforms_twenty_five_nits_more():
    sample = analyze_curve_sample(25.0)

    assert sample.smooth_nits > sample.colorcontrol_nits

    assert (
        sample.smooth_distance_from_identity_nits
        > sample.colorcontrol_distance_from_identity_nits
    )


def test_curves_match_at_midpoint():
    sample = analyze_curve_sample(50.0)

    assert sample.smooth_nits == pytest.approx(
        sample.colorcontrol_nits,
        abs=1e-9,
    )

    assert sample.difference_nits == pytest.approx(
        0.0,
        abs=1e-9,
    )


def test_smooth_is_closer_to_identity_at_seventy_five_nits():
    sample = analyze_curve_sample(75.0)

    assert (
        sample.smooth_distance_from_identity_nits
        < sample.colorcontrol_distance_from_identity_nits
    )


def test_both_curves_are_identity_at_sdr_white():
    sample = analyze_curve_sample(100.0)

    assert sample.colorcontrol_nits == pytest.approx(
        100.0,
        abs=1e-7,
    )

    assert sample.smooth_nits == pytest.approx(
        100.0,
        abs=1e-7,
    )

def test_generates_default_samples():
    samples = sample_curves()

    assert tuple(
        sample.input_nits for sample in samples
    ) == DEFAULT_SAMPLE_LUMINANCES


def test_accepts_custom_sample_luminances():
    samples = sample_curves((1.0, 20.0, 100.0))

    assert tuple(
        sample.input_nits for sample in samples
    ) == (1.0, 20.0, 100.0)


def test_complete_analysis_uses_requested_lut_size():
    analysis = analyze_curves(entries=1024)

    assert analysis.entries == 1024
    assert len(analysis.samples) == len(
        DEFAULT_SAMPLE_LUMINANCES
    )


def test_quantized_entry_counts_cover_complete_lut():
    analysis = analyze_curves(entries=1024)

    assert (
        analysis.quantized_smooth_brighter_entries
        + analysis.quantized_smooth_darker_entries
        + analysis.quantized_equal_entries
        == analysis.entries
    )

    assert (
        analysis.quantized_different_entries
        == analysis.quantized_smooth_brighter_entries
        + analysis.quantized_smooth_darker_entries
    )


def test_curves_have_real_quantized_differences():
    analysis = analyze_curves(entries=1024)

    assert 0 < analysis.quantized_different_entries < 1024


def test_maximum_difference_occurs_below_sdr_white():
    analysis = analyze_curves(entries=1024)

    assert analysis.max_absolute_difference_nits > 0.0
    assert 0.0 < analysis.max_difference_input_nits < 100.0

    assert abs(
        analysis.max_signed_difference_nits
    ) == pytest.approx(
        analysis.max_absolute_difference_nits
    )