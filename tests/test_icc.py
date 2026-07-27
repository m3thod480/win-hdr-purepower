import struct

import pytest

from hdrfix import ICCFormatError, inspect_profile, parse_profile, read_profile


def _fixed(value):
    return int(value * 65536)


def _sf32(values, *, signature=b"sf32", reserved=0):
    return struct.pack(
        f">4sI{len(values)}i",
        signature,
        reserved,
        *(_fixed(value) for value in values),
    )


def _mhc2(
    red=(-0.5, 0.25, 1.0),
    green=(0.0, 0.5, 1.0),
    blue=(0.125, 0.75, 1.0),
    *,
    min_luminance=-0.5,
    max_luminance=520.25,
):
    assert len(red) == len(green) == len(blue)
    matrix_data = struct.pack(
        ">12i",
        _fixed(1),
        0,
        0,
        0,
        0,
        _fixed(1),
        0,
        0,
        0,
        0,
        _fixed(1),
        0,
    )
    red_data = _sf32(red)
    green_data = _sf32(green)
    blue_data = _sf32(blue)
    matrix_offset = 36
    red_offset = matrix_offset + len(matrix_data)
    green_offset = red_offset + len(red_data)
    blue_offset = green_offset + len(green_data)
    header = struct.pack(
        ">4sIIiiIIII",
        b"MHC2",
        0,
        len(red),
        _fixed(min_luminance),
        _fixed(max_luminance),
        matrix_offset,
        red_offset,
        green_offset,
        blue_offset,
    )
    return header + matrix_data + red_data + green_data + blue_data


def _profile(tags=()):
    header = bytearray(128)
    header[36:40] = b"acsp"
    table_end = 132 + len(tags) * 12
    entries = bytearray()
    payloads = bytearray()
    for signature, payload in tags:
        offset = table_end + len(payloads)
        entries += struct.pack(">4sII", signature, offset, len(payload))
        payloads += payload
    result = header + struct.pack(">I", len(tags)) + entries + payloads
    struct.pack_into(">I", result, 0, len(result))
    return bytes(result)


def test_parses_tag_table_and_mhc2_values_as_big_endian_s15fixed16():
    data = _profile(((b"desc", b"text"), (b"MHC2", _mhc2())))

    profile = parse_profile(data)

    assert profile.file_size == len(data)
    assert profile.signature == "acsp"
    assert [tag.signature for tag in profile.tags] == ["desc", "MHC2"]
    assert profile.tags[0].offset == 156
    assert profile.tags[0].size == 4
    assert profile.mhc2 is not None
    assert profile.mhc2.lut_entry_count == 3
    assert profile.mhc2.min_luminance == -0.5
    assert profile.mhc2.max_luminance == 520.25
    assert profile.mhc2.matrix_offset == 36
    assert profile.mhc2.red_lut_offset == 84
    assert profile.mhc2.green_lut_offset == 104
    assert profile.mhc2.blue_lut_offset == 124
    assert profile.mhc2.red_lut == (-0.5, 0.25, 1.0)
    assert profile.mhc2.green_lut == (0.0, 0.5, 1.0)
    assert profile.mhc2.blue_lut == (0.125, 0.75, 1.0)


def test_profile_without_mhc2_is_valid():
    profile = parse_profile(_profile(((b"desc", b"text"),)))

    assert profile.mhc2 is None


@pytest.mark.parametrize("size", [0, 36, 127, 128, 131])
def test_rejects_files_shorter_than_132_bytes(size):
    with pytest.raises(ICCFormatError, match="al menos 132"):
        parse_profile(bytes(size))


def test_rejects_invalid_acsp_signature():
    data = bytearray(132)

    with pytest.raises(ICCFormatError, match="bytes 36-39.*acsp"):
        parse_profile(bytes(data))


def test_rejects_truncated_tag_table():
    data = bytearray(_profile())
    struct.pack_into(">I", data, 128, 1)

    with pytest.raises(ICCFormatError, match="Tabla de etiquetas ICC truncada"):
        parse_profile(bytes(data))


def test_rejects_tag_whose_declared_range_is_outside_file():
    data = bytearray(_profile(((b"desc", b"abcd"),)))
    struct.pack_into(">II", data, 136, len(data) - 1, 4)

    with pytest.raises(ICCFormatError, match="desc.*fuera del archivo"):
        parse_profile(bytes(data))


def test_rejects_mhc2_shorter_than_36_bytes():
    data = _profile(((b"MHC2", b"MHC2" + bytes(31)),))

    with pytest.raises(ICCFormatError, match="MHC2 truncada.*36"):
        parse_profile(data)


def test_rejects_invalid_internal_mhc2_signature():
    payload = bytearray(_mhc2())
    payload[0:4] = b"NOPE"

    with pytest.raises(ICCFormatError, match="Firma interna de MHC2 inválida"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_rejects_nonzero_mhc2_reserved_field():
    payload = bytearray(_mhc2())
    struct.pack_into(">I", payload, 4, 1)

    with pytest.raises(ICCFormatError, match="reservado de MHC2.*esperaba 0"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_rejects_more_than_4096_lut_entries_before_reading_them():
    payload = struct.pack(
        ">4sIIiiIIII", b"MHC2", 0, 4097, 0, 0, 0, 0, 0, 0
    )

    with pytest.raises(ICCFormatError, match="máximo admitido.*4096"):
        parse_profile(_profile(((b"MHC2", payload),)))


@pytest.mark.parametrize(
    ("offset_field", "channel"),
    ((24, "roja"), (28, "verde"), (32, "azul")),
)
def test_rejects_lut_offsets_outside_the_mhc2_tag(offset_field, channel):
    payload = bytearray(_mhc2())
    struct.pack_into(">I", payload, offset_field, len(payload) - 4)

    with pytest.raises(ICCFormatError, match=rf"LUT {channel}.*fuera de límites"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_rejects_lut_offset_inside_mhc2_header():
    payload = bytearray(_mhc2())
    struct.pack_into(">I", payload, 24, 4)

    with pytest.raises(ICCFormatError, match="Offset de la LUT roja.*al menos 36"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_rejects_non_sf32_lut():
    payload = bytearray(_mhc2())
    red_offset = struct.unpack_from(">I", payload, 24)[0]
    payload[red_offset : red_offset + 4] = b"nope"

    with pytest.raises(ICCFormatError, match="LUT roja inválida.*sf32"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_rejects_nonzero_sf32_reserved_field():
    payload = bytearray(_mhc2())
    red_offset = struct.unpack_from(">I", payload, 24)[0]
    struct.pack_into(">I", payload, red_offset + 4, 1)

    with pytest.raises(ICCFormatError, match="reservado de la LUT roja.*esperaba 0"):
        parse_profile(_profile(((b"MHC2", bytes(payload)),)))


def test_zero_entries_represents_identity_without_lut_data():
    payload = struct.pack(
        ">4sIIiiIIII", b"MHC2", 0, 0, 0, _fixed(1000), 0, 0, 0, 0
    )

    profile = parse_profile(_profile(((b"MHC2", payload),)))

    assert profile.mhc2 is not None
    assert profile.mhc2.red_lut == ()
    assert profile.mhc2.green_lut == ()
    assert profile.mhc2.blue_lut == ()


def test_file_helpers_read_bytes_without_modifying_the_profile(tmp_path):
    path = tmp_path / "perfil de prueba.icm"
    original = _profile(((b"MHC2", _mhc2()),))
    path.write_bytes(original)

    assert read_profile(path) == original
    assert inspect_profile(path).mhc2 is not None
    assert path.read_bytes() == original
