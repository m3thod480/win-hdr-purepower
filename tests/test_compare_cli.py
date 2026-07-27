from pathlib import Path
import struct

import pytest

from hdrfix.compare import build_parser, main


def test_compare_parser_accepts_two_profile_paths():
    parser = build_parser()

    arguments = parser.parse_args(
        ["windows.icc", "colorcontrol.icm"]
    )

    assert arguments.left == Path("windows.icc")
    assert arguments.right == Path("colorcontrol.icm")


def _fixed(value: float) -> int:
    return int(value * 65536)


def _profile(lut: tuple[float, ...]) -> bytes:
    matrix_data = struct.pack(
        ">12i",
        _fixed(1.0),
        0,
        0,
        0,
        0,
        _fixed(1.0),
        0,
        0,
        0,
        0,
        _fixed(1.0),
        0,
    )
    lut_data = struct.pack(
        f">4sI{len(lut)}i",
        b"sf32",
        0,
        *(_fixed(value) for value in lut),
    )
    matrix_offset = 36
    red_lut_offset = matrix_offset + len(matrix_data)
    green_lut_offset = red_lut_offset + len(lut_data)
    blue_lut_offset = green_lut_offset + len(lut_data)
    mhc2 = (
        struct.pack(
            ">4sIIiiIIII",
            b"MHC2",
            0,
            len(lut),
            _fixed(0.0),
            _fixed(520.0),
            matrix_offset,
            red_lut_offset,
            green_lut_offset,
            blue_lut_offset,
        )
        + matrix_data
        + lut_data * 3
    )

    header = bytearray(128)
    header[36:40] = b"acsp"
    payload_offset = 144
    profile = (
        header
        + struct.pack(">I", 1)
        + struct.pack(">4sII", b"MHC2", payload_offset, len(mhc2))
        + mhc2
    )
    struct.pack_into(">I", profile, 0, len(profile))
    return bytes(profile)


def test_compare_cli_prints_both_profiles_without_modifying_them(
    tmp_path,
    capsys,
):
    left_path = tmp_path / "windows HDR.icc"
    right_path = tmp_path / "perfil corregido.icm"
    left_original = _profile((0.0, 1.0))
    right_original = _profile((0.0, 0.5))
    left_path.write_bytes(left_original)
    right_path.write_bytes(right_original)

    result = main([str(left_path), str(right_path)])

    output = capsys.readouterr().out
    assert result == 0
    assert f"Perfil izquierdo: {left_path}" in output
    assert f"Perfil derecho: {right_path}" in output
    assert output.count("MHC2: Sí") == 2
    assert "Luminancia mínima: 0.0" in output
    assert "Luminancia máxima: 520.0" in output
    assert "Número de entradas de LUT: 2" in output
    assert "Canales RGB iguales: Sí" in output
    assert "LUT de identidad: Sí" in output
    assert "LUT de identidad: No" in output
    assert "Misma luminancia mínima: Sí" in output
    assert "Misma luminancia máxima: Sí" in output
    assert "Mismo número de entradas de LUT: Sí" in output
    assert "Mismo estado de identidad: No" in output
    assert left_path.read_bytes() == left_original
    assert right_path.read_bytes() == right_original


def test_compare_cli_reports_malformed_profile_without_traceback(
    tmp_path,
    capsys,
):
    left_path = tmp_path / "valido.icc"
    right_path = tmp_path / "roto.icm"
    left_path.write_bytes(_profile((0.0, 1.0)))
    malformed = b"not an ICC profile"
    right_path.write_bytes(malformed)

    with pytest.raises(SystemExit) as exit_info:
        main([str(left_path), str(right_path)])

    error = capsys.readouterr().err
    assert exit_info.value.code == 2
    assert f"no se pudo inspeccionar '{right_path}'" in error
    assert "al menos 132 bytes" in error
    assert "Traceback" not in error
    assert right_path.read_bytes() == malformed
