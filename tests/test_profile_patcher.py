from collections.abc import Callable
import hashlib
from pathlib import Path
import struct

import pytest

from hdrfix.curves import (
    generate_shadow_stretch_lut,
    quantize_s15_fixed_16,
)
from hdrfix.icc import ICCFormatError, SF32_HEADER_SIZE, parse_profile
from hdrfix.profile_patcher import (
    ICC_PROFILE_ID_OFFSET,
    ICC_PROFILE_ID_SIZE,
    build_patched_profile,
    calculate_profile_id,
    replace_mhc2_luts,
    set_profile_id,
)


REFERENCE_PROFILE = Path("samples/hdr_cc.icm")
requires_reference_profile = pytest.mark.skipif(
    not REFERENCE_PROFILE.exists(),
    reason="No está disponible el perfil ColorControl de referencia.",
)


def _quantized(lut: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(
        quantize_s15_fixed_16(value) / 65_536
        for value in lut
    )


def test_profile_id_has_16_bytes(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile()

    profile_id = calculate_profile_id(profile_data)

    assert len(profile_id) == ICC_PROFILE_ID_SIZE == 16


def test_profile_id_uses_the_icc_mandated_zeroed_header_fields(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile()
    digest_input = bytearray(profile_data)
    digest_input[44:48] = bytes(4)
    digest_input[64:68] = bytes(4)
    digest_input[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] = bytes(ICC_PROFILE_ID_SIZE)
    expected_id = hashlib.md5(
        digest_input,
        usedforsecurity=False,
    ).digest()

    assert calculate_profile_id(profile_data) == expected_id


def test_setting_profile_id_is_idempotent(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile()

    with_id = set_profile_id(profile_data)
    set_again = set_profile_id(with_id)

    assert set_again == with_id
    assert with_id[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] == calculate_profile_id(with_id)


@pytest.mark.parametrize(
    "declared_size_adjustment",
    (None, -1, 1),
    ids=("zero", "smaller", "larger"),
)
def test_rejects_malformed_declared_profile_sizes(
    make_mhc2_profile: Callable[..., bytes],
    declared_size_adjustment: int | None,
):
    profile_data = make_mhc2_profile()
    malformed = bytearray(profile_data)
    declared_size = (
        0
        if declared_size_adjustment is None
        else len(profile_data) + declared_size_adjustment
    )
    struct.pack_into(">I", malformed, 0, declared_size)
    malformed_data = bytes(malformed)
    replacement_lut = (0.125, 0.875)

    with pytest.raises(ICCFormatError):
        calculate_profile_id(malformed_data)
    with pytest.raises(ICCFormatError):
        set_profile_id(malformed_data)
    with pytest.raises(ICCFormatError):
        replace_mhc2_luts(malformed_data, replacement_lut)
    with pytest.raises(ICCFormatError):
        build_patched_profile(malformed_data, replacement_lut)


def test_build_patched_profile_replaces_all_three_channels(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile(
        (0.0, 1.0),
        (0.25, 0.75),
        (0.5, 0.625),
    )
    replacement_lut = (0.125, 0.875)

    patched_data = build_patched_profile(
        profile_data,
        replacement_lut,
    )
    patched_profile = parse_profile(patched_data)

    assert patched_profile.mhc2 is not None
    expected_lut = _quantized(replacement_lut)
    assert patched_profile.mhc2.red_lut == expected_lut
    assert patched_profile.mhc2.green_lut == expected_lut
    assert patched_profile.mhc2.blue_lut == expected_lut
    assert patched_data[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] == calculate_profile_id(patched_data)


def test_build_only_changes_lut_values_and_profile_id(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile(
        (0.0, 1.0),
        (0.25, 0.75),
        (0.5, 0.625),
    )
    replacement_lut = (0.125, 0.875)
    profile = parse_profile(profile_data)

    assert profile.mhc2 is not None
    mhc2_tag = next(
        tag for tag in profile.tags
        if tag.signature == "MHC2"
    )
    allowed_changes = set(
        range(
            ICC_PROFILE_ID_OFFSET,
            ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE,
        )
    )
    lut_size = profile.mhc2.lut_entry_count * 4
    for relative_offset in (
        profile.mhc2.red_lut_offset,
        profile.mhc2.green_lut_offset,
        profile.mhc2.blue_lut_offset,
    ):
        values_start = (
            mhc2_tag.offset
            + relative_offset
            + SF32_HEADER_SIZE
        )
        allowed_changes.update(
            range(values_start, values_start + lut_size)
        )

    patched_data = build_patched_profile(
        profile_data,
        replacement_lut,
    )
    changed_offsets = {
        offset
        for offset, (original, patched) in enumerate(
            zip(profile_data, patched_data, strict=True)
        )
        if original != patched
    }

    assert changed_offsets
    assert changed_offsets <= allowed_changes


def test_patch_operations_preserve_the_source_bytes_object(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile()
    original_copy = bytes(bytearray(profile_data))
    replacement_lut = (0.125, 0.875)

    calculate_profile_id(profile_data)
    with_id = set_profile_id(profile_data)
    replaced = replace_mhc2_luts(profile_data, replacement_lut)
    patched = build_patched_profile(profile_data, replacement_lut)

    assert profile_data == original_copy
    assert with_id is not profile_data
    assert replaced is not profile_data
    assert patched is not profile_data


def test_rejects_lut_with_wrong_number_of_entries(
    make_mhc2_profile: Callable[..., bytes],
):
    profile_data = make_mhc2_profile()

    with pytest.raises(ValueError, match="mismo número"):
        replace_mhc2_luts(
            profile_data,
            (0.0, 0.5, 1.0),
        )


@requires_reference_profile
def test_replaces_reference_profile_luts_with_final_curve():
    original_data = REFERENCE_PROFILE.read_bytes()
    original_profile = parse_profile(original_data)

    assert original_profile.mhc2 is not None
    final_lut = generate_shadow_stretch_lut(
        entries=original_profile.mhc2.lut_entry_count,
        sdr_white_nits=100.0,
        sdr_black_nits=0.0,
    )

    modified_data = build_patched_profile(
        original_data,
        final_lut,
    )
    modified_profile = parse_profile(modified_data)

    assert modified_profile.mhc2 is not None
    assert modified_profile.mhc2.red_lut == pytest.approx(
        final_lut,
        abs=1 / 65_536,
    )
    assert modified_profile.mhc2.green_lut == pytest.approx(
        final_lut,
        abs=1 / 65_536,
    )
    assert modified_profile.mhc2.blue_lut == pytest.approx(
        final_lut,
        abs=1 / 65_536,
    )


@requires_reference_profile
def test_reference_profile_has_a_valid_profile_id():
    profile_data = REFERENCE_PROFILE.read_bytes()
    stored_id = profile_data[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ]

    assert stored_id == calculate_profile_id(profile_data)
