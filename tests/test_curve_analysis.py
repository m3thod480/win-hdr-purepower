import pytest

from hdrfix.curve_analysis import analyze_curve_sample


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