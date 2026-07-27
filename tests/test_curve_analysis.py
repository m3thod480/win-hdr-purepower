import pytest

from hdrfix.curve_analysis import (
    DEFAULT_SAMPLE_LUMINANCES,
    analyze_curve_sample,
    analyze_curves,
    sample_curves,
)


def test_shadow_stretch_preserves_more_detail_near_black():
    sample = analyze_curve_sample(1.0)

    assert sample.shadow_stretch_nits > sample.pure_power_nits
    assert sample.shadow_stretch_nits <= sample.input_nits
    assert sample.shadow_stretch_minus_pure_power_nits > 0.0


def test_sample_reports_deltas_from_identity():
    sample = analyze_curve_sample(5.0)

    assert sample.pure_power_delta_nits == pytest.approx(
        sample.pure_power_nits - sample.input_nits
    )
    assert sample.shadow_stretch_delta_nits == pytest.approx(
        sample.shadow_stretch_nits - sample.input_nits
    )


def test_shadow_stretch_matches_pure_power_at_shadow_end():
    sample = analyze_curve_sample(10.0)

    assert sample.shadow_stretch_nits == pytest.approx(
        sample.pure_power_nits,
        abs=1e-9,
    )
    assert sample.shadow_stretch_minus_pure_power_nits == pytest.approx(
        0.0,
        abs=1e-9,
    )


def test_shadow_stretch_matches_pure_power_above_shadow_end():
    sample = analyze_curve_sample(25.0)

    assert sample.shadow_stretch_nits == pytest.approx(
        sample.pure_power_nits,
        abs=1e-9,
    )


def test_both_curves_are_identity_at_sdr_white():
    sample = analyze_curve_sample(100.0)

    assert sample.pure_power_nits == pytest.approx(100.0, abs=1e-7)
    assert sample.shadow_stretch_nits == pytest.approx(
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


def test_curves_have_real_quantized_differences():
    analysis = analyze_curves(entries=1024)

    assert 0 < analysis.quantized_different_entries < analysis.entries


def test_maximum_difference_occurs_in_affected_shadow_region():
    analysis = analyze_curves(entries=1024)

    assert analysis.max_difference_nits > 0.0
    assert 0.0 < analysis.max_difference_input_nits < 10.0
