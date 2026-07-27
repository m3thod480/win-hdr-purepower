import pytest

from hdrfix.curves import nits_to_pq, pq_to_nits


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