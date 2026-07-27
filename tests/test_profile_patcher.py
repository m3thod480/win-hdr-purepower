from pathlib import Path

import pytest

from hdrfix.curves import generate_smooth_anchored_lut
from hdrfix.icc import parse_profile
from hdrfix.profile_patcher import replace_mhc2_luts


REFERENCE_PROFILE = Path("samples/hdr_cc.icm")


@pytest.mark.skipif(
    not REFERENCE_PROFILE.exists(),
    reason="No está disponible el perfil ColorControl de referencia.",
)
def test_replaces_all_three_mhc2_luts_with_smooth_curve():
    original_data = REFERENCE_PROFILE.read_bytes()
    original_profile = parse_profile(original_data)

    assert original_profile.mhc2 is not None

    smooth_lut = generate_smooth_anchored_lut(
        entries=original_profile.mhc2.lut_entry_count,
        gamma=2.2,
        sdr_white_nits=100.0,
        sdr_black_nits=0.0,
    )

    modified_data = replace_mhc2_luts(
        original_data,
        smooth_lut,
    )

    modified_profile = parse_profile(modified_data)

    assert modified_profile.mhc2 is not None
    assert modified_profile.mhc2.red_lut == pytest.approx(
        smooth_lut,
        abs=1 / 65_536,
    )
    assert modified_profile.mhc2.green_lut == pytest.approx(
        smooth_lut,
        abs=1 / 65_536,
    )
    assert modified_profile.mhc2.blue_lut == pytest.approx(
        smooth_lut,
        abs=1 / 65_536,
    )


@pytest.mark.skipif(
    not REFERENCE_PROFILE.exists(),
    reason="No está disponible el perfil ColorControl de referencia.",
)
def test_does_not_modify_original_bytes_object():
    original_data = REFERENCE_PROFILE.read_bytes()
    original_copy = bytes(original_data)

    profile = parse_profile(original_data)

    assert profile.mhc2 is not None

    smooth_lut = generate_smooth_anchored_lut(
        entries=profile.mhc2.lut_entry_count,
    )

    replace_mhc2_luts(original_data, smooth_lut)

    assert original_data == original_copy


@pytest.mark.skipif(
    not REFERENCE_PROFILE.exists(),
    reason="No está disponible el perfil ColorControl de referencia.",
)
def test_rejects_lut_with_wrong_number_of_entries():
    original_data = REFERENCE_PROFILE.read_bytes()

    with pytest.raises(ValueError, match="mismo número"):
        replace_mhc2_luts(
            original_data,
            (0.0, 1.0),
        )