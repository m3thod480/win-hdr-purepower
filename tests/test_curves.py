import pytest

from hdrfix.curves import (
    colorcontrol_pure_power_sample,
    luminance_to_srgb_signal,
    nits_to_pq,
    pq_to_nits,
)

def test_pq_zero_represents_zero_nits():
    assert pq_to_nits(0.0) == pytest.approx(0.0)


def test_pq_one_represents_ten_thousand_nits():
    assert pq_to_nits(1.0) == pytest.approx(10_000.0)


def test_one_hundred_nits_has_expected_pq_value():
    assert nits_to_pq(100.0) == pytest.approx(
        0.5080784215,
        abs=1e-10,
    )


def test_monitor_peak_has_expected_pq_value():
    assert nits_to_pq(520.0) == pytest.approx(
        0.6808180930,
        abs=1e-10,
    )


@pytest.mark.parametrize(
    "luminance",
    [
        0.0,
        0.1,
        1.0,
        10.0,
        50.0,
        100.0,
        520.0,
        1_000.0,
        10_000.0,
    ],
)
def test_pq_round_trip(luminance: float):
    encoded = nits_to_pq(luminance)
    decoded = pq_to_nits(encoded)

    assert decoded == pytest.approx(
        luminance,
        abs=1e-7,
    )


@pytest.mark.parametrize("signal", [-0.1, 1.1])
def test_rejects_invalid_pq_signal(signal: float):
    with pytest.raises(ValueError):
        pq_to_nits(signal)


@pytest.mark.parametrize("luminance", [-1.0, 10_001.0])
def test_rejects_invalid_luminance(luminance: float):
    with pytest.raises(ValueError):
        nits_to_pq(luminance)

def test_black_luminance_encodes_to_zero():
    assert luminance_to_srgb_signal(
        luminance=0.0,
        white_luminance=100.0,
    ) == pytest.approx(0.0)


def test_white_luminance_encodes_to_one():
    assert luminance_to_srgb_signal(
        luminance=100.0,
        white_luminance=100.0,
    ) == pytest.approx(1.0)


def test_half_linear_luminance_encodes_as_srgb():
    assert luminance_to_srgb_signal(
        luminance=50.0,
        white_luminance=100.0,
    ) == pytest.approx(
        0.7353569830524495,
        abs=1e-12,
    )


def test_luminance_below_black_is_clamped():
    assert luminance_to_srgb_signal(
        luminance=-10.0,
        white_luminance=100.0,
    ) == pytest.approx(0.0)


def test_luminance_above_white_is_clamped():
    assert luminance_to_srgb_signal(
        luminance=200.0,
        white_luminance=100.0,
    ) == pytest.approx(1.0)


def test_rejects_invalid_luminance_range():
    with pytest.raises(ValueError):
        luminance_to_srgb_signal(
            luminance=50.0,
            white_luminance=0.0,
            black_luminance=0.0,
        )

def test_colorcontrol_curve_darkens_low_luminance():
    input_pq = nits_to_pq(1.0)

    output_pq = colorcontrol_pure_power_sample(input_pq)

    assert output_pq < input_pq


@pytest.mark.parametrize(
    "luminance",
    [100.0, 520.0, 1_000.0],
)
def test_colorcontrol_curve_is_identity_at_and_above_sdr_white(
    luminance: float,
):
    input_pq = nits_to_pq(luminance)

    output_pq = colorcontrol_pure_power_sample(
        input_pq,
        sdr_white_nits=100.0,
    )

    assert output_pq == pytest.approx(
        input_pq,
        abs=1e-12,
    )


def test_colorcontrol_known_sample():
    input_pq = 256 / 1023

    output_pq = colorcontrol_pure_power_sample(input_pq)

    assert output_pq == pytest.approx(
        0.24558283238708356,
        abs=1e-12,
    )


@pytest.mark.parametrize(
    "gamma",
    [0.0, -1.0],
)
def test_colorcontrol_curve_rejects_invalid_gamma(
    gamma: float,
):
    with pytest.raises(ValueError):
        colorcontrol_pure_power_sample(
            input_pq=0.5,
            gamma=gamma,
        )


def test_colorcontrol_curve_rejects_invalid_sdr_range():
    with pytest.raises(ValueError):
        colorcontrol_pure_power_sample(
            input_pq=0.5,
            sdr_black_nits=100.0,
            sdr_white_nits=100.0,
        )