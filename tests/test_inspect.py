import json
import struct

import pytest

from hdrfix.inspect import main


def _identity_profile():
    mhc2 = struct.pack(
        ">4sIIiiIIII", b"MHC2", 0, 0, 0, 520 * 65536, 0, 0, 0, 0
    )
    header = bytearray(128)
    header[36:40] = b"acsp"
    payload_offset = 144
    result = (
        header
        + struct.pack(">I", 1)
        + struct.pack(">4sII", b"MHC2", payload_offset, len(mhc2))
        + mhc2
    )
    struct.pack_into(">I", result, 0, len(result))
    return bytes(result)


def test_cli_prints_tag_table_and_mhc2_header(tmp_path, capsys):
    path = tmp_path / "perfil HDR.icc"
    original = _identity_profile()
    path.write_bytes(original)

    result = main([str(path)])

    output = capsys.readouterr().out
    assert result == 0
    assert "Firma ICC: acsp" in output
    assert "MHC2  offset=144  tamaño=36" in output
    assert "MHC2: encontrada" in output
    assert "Entradas de LUT: 0" in output
    assert "Luminancia máxima: 520.0 nits" in output
    assert path.read_bytes() == original


def test_cli_can_emit_machine_readable_json(tmp_path, capsys):
    path = tmp_path / "perfil.icm"
    path.write_bytes(_identity_profile())

    assert main(["--json", str(path)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["path"] == str(path)
    assert result["signature"] == "acsp"
    assert result["tags"] == [{"signature": "MHC2", "offset": 144, "size": 36}]
    assert result["mhc2"]["lut_entry_count"] == 0
    assert result["mhc2"]["max_luminance"] == 520.0
    assert result["mhc2"]["red_lut"] == []


def test_cli_reports_format_errors_without_traceback(tmp_path, capsys):
    path = tmp_path / "roto.icc"
    path.write_bytes(b"not an ICC profile")

    with pytest.raises(SystemExit) as exit_info:
        main([str(path)])

    error = capsys.readouterr().err
    assert exit_info.value.code == 2
    assert "no se pudo inspeccionar" in error
    assert "al menos 132 bytes" in error
    assert "Traceback" not in error
