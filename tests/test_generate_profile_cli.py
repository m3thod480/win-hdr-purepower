from pathlib import Path

import pytest

from hdrfix.curves import (
    generate_shadow_stretch_lut,
    quantize_s15_fixed_16,
)
from hdrfix.generate_profile import build_parser, main
from hdrfix.icc import parse_profile


def _write_template(
    path: Path,
    make_mhc2_profile,
    *,
    entries: int = 1024,
) -> bytes:
    last_index = entries - 1
    data = make_mhc2_profile(
        red_lut=tuple(
            index / last_index
            for index in range(entries)
        ),
    )
    path.write_bytes(data)
    return data


def test_parser_exposes_only_fixed_curve_generation_options():
    arguments = build_parser().parse_args(
        [
            "template.icm",
            "output.icm",
            "--sdr-white",
            "80",
            "--sdr-black",
            "0.01",
            "--force",
        ]
    )

    assert arguments.template == Path("template.icm")
    assert arguments.output == Path("output.icm")
    assert arguments.sdr_white == 80.0
    assert arguments.sdr_black == 0.01
    assert arguments.force is True
    assert set(vars(arguments)) == {
        "template",
        "output",
        "sdr_white",
        "sdr_black",
        "force",
    }


def test_cli_generates_fixed_shadow_stretch_in_all_channels(
    tmp_path,
    capsys,
    make_mhc2_profile,
):
    entries = 1024
    template_path = tmp_path / "template HDR.icm"
    output_path = tmp_path / "fixed shadow stretch.icm"
    template_data = _write_template(
        template_path,
        make_mhc2_profile,
        entries=entries,
    )

    result = main(
        [
            str(template_path),
            str(output_path),
            "--sdr-white",
            "80",
            "--sdr-black",
            "0.01",
        ]
    )

    generated_data = output_path.read_bytes()
    generated_profile = parse_profile(generated_data)
    output = capsys.readouterr().out
    expected_lut = generate_shadow_stretch_lut(
        entries=entries,
        sdr_white_nits=80.0,
        sdr_black_nits=0.01,
    )
    expected_quantized = tuple(
        quantize_s15_fixed_16(value) / 65_536
        for value in expected_lut
    )

    assert result == 0
    assert generated_profile.mhc2 is not None
    assert generated_profile.mhc2.lut_entry_count == entries
    assert generated_profile.mhc2.red_lut == expected_quantized
    assert generated_profile.mhc2.green_lut == expected_quantized
    assert generated_profile.mhc2.blue_lut == expected_quantized
    assert len(generated_data[84:100]) == 16
    assert generated_data[84:100] != bytes(16)
    assert template_path.read_bytes() == template_data
    assert "Curve: Pure Power 2.2 + Shadow Stretch" in output
    assert "Shadow end: 10.0 nits" in output
    assert "Shadow strength: 0.25" in output
    assert "Entradas: 1024" in output
    assert "Negro SDR: 0.01 nits" in output
    assert "Blanco SDR: 80.0 nits" in output
    assert str(output_path) in output
    assert generated_data[84:100].hex() in output.lower()


def test_cli_rejects_existing_output_without_modifying_either_file(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_path = tmp_path / "existing.icm"
    template_data = _write_template(template_path, make_mhc2_profile)
    existing_data = b"existing output must be preserved"
    output_path.write_bytes(existing_data)

    with pytest.raises(SystemExit) as error:
        main([str(template_path), str(output_path)])

    assert error.value.code == 2
    assert template_path.read_bytes() == template_data
    assert output_path.read_bytes() == existing_data


def test_cli_force_overwrites_existing_output_with_parseable_profile(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_path = tmp_path / "existing.icm"
    template_data = _write_template(template_path, make_mhc2_profile)
    output_path.write_bytes(b"old output")

    result = main(
        [
            str(template_path),
            str(output_path),
            "--force",
        ]
    )

    generated_profile = parse_profile(output_path.read_bytes())

    assert result == 0
    assert generated_profile.mhc2 is not None
    assert generated_profile.mhc2.lut_entry_count == 1024
    assert template_path.read_bytes() == template_data


def test_cli_creates_missing_output_directory_and_parseable_profile(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_directory = tmp_path / "generated"
    output_path = output_directory / "profile.icm"
    template_data = _write_template(template_path, make_mhc2_profile)

    assert not output_directory.exists()

    result = main([str(template_path), str(output_path)])
    generated_profile = parse_profile(output_path.read_bytes())

    assert result == 0
    assert output_directory.is_dir()
    assert generated_profile.mhc2 is not None
    assert generated_profile.mhc2.lut_entry_count == 1024
    assert template_path.read_bytes() == template_data


def test_cli_creates_multiple_nested_output_directories(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_path = (
        tmp_path
        / "generated"
        / "profiles"
        / "hdr"
        / "profile.icm"
    )
    template_data = _write_template(template_path, make_mhc2_profile)

    assert not output_path.parent.exists()

    result = main([str(template_path), str(output_path)])
    generated_profile = parse_profile(output_path.read_bytes())

    assert result == 0
    assert output_path.parent.is_dir()
    assert generated_profile.mhc2 is not None
    assert generated_profile.mhc2.lut_entry_count == 1024
    assert template_path.read_bytes() == template_data


@pytest.mark.parametrize("entries", [2, 512, 4096])
def test_cli_rejects_template_without_exactly_1024_entries(
    entries,
    tmp_path,
    capsys,
    make_mhc2_profile,
):
    template_path = tmp_path / f"template-{entries}.icm"
    output_path = tmp_path / "generated" / "profile.icm"
    template_data = _write_template(
        template_path,
        make_mhc2_profile,
        entries=entries,
    )

    with pytest.raises(SystemExit) as error:
        main([str(template_path), str(output_path)])

    message = capsys.readouterr().err
    assert error.value.code == 2
    assert f"Detected {entries} MHC2 LUT entries" in message
    assert "HDRFix v0.1" in message
    assert "1024-entry MHC2 template" in message
    assert (
        "two-entry Windows HDR Calibration identity profiles "
        "are unsuitable"
    ) in message
    assert template_path.read_bytes() == template_data
    assert not output_path.exists()
    assert not output_path.parent.exists()


def test_cli_accepts_template_with_exactly_1024_entries(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template-1024.icm"
    output_path = tmp_path / "generated.icm"
    template_data = _write_template(
        template_path,
        make_mhc2_profile,
        entries=1024,
    )

    result = main([str(template_path), str(output_path)])
    generated_profile = parse_profile(output_path.read_bytes())

    assert result == 0
    assert generated_profile.mhc2 is not None
    assert generated_profile.mhc2.lut_entry_count == 1024
    assert template_path.read_bytes() == template_data


def test_cli_rejects_same_input_and_output_even_with_force(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    template_data = _write_template(template_path, make_mhc2_profile)

    with pytest.raises(SystemExit) as error:
        main(
            [
                str(template_path),
                str(template_path),
                "--force",
            ]
        )

    assert error.value.code == 2
    assert template_path.read_bytes() == template_data


@pytest.mark.parametrize(
    "arguments",
    [
        ["--curve", "shadow-stretch"],
        ["--entries", "3"],
        ["--gamma", "2.2"],
        ["--shadow-end", "10"],
        ["--shadow-strength", "0.25"],
        ["--sdr-white-nits", "100"],
        ["--sdr-black-nits", "0"],
    ],
)
def test_cli_rejects_removed_options(
    arguments,
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_path = tmp_path / "generated.icm"
    template_data = _write_template(template_path, make_mhc2_profile)

    with pytest.raises(SystemExit) as error:
        main(
            [
                str(template_path),
                str(output_path),
                *arguments,
            ]
        )

    assert error.value.code == 2
    assert template_path.read_bytes() == template_data
    assert not output_path.exists()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--sdr-black", "-1"],
        ["--sdr-white", "0"],
        ["--sdr-white", "9"],
        ["--sdr-white", "10001"],
        ["--sdr-black", "100", "--sdr-white", "100"],
        ["--sdr-black", "nan"],
        ["--sdr-white", "inf"],
    ],
)
def test_cli_rejects_invalid_luminance_parameters(
    arguments,
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "template.icm"
    output_path = tmp_path / "generated.icm"
    template_data = _write_template(template_path, make_mhc2_profile)

    with pytest.raises(SystemExit) as error:
        main(
            [
                str(template_path),
                str(output_path),
                *arguments,
            ]
        )

    assert error.value.code == 2
    assert template_path.read_bytes() == template_data
    assert not output_path.exists()


def test_cli_rejects_template_without_mhc2(
    tmp_path,
    make_mhc2_profile,
):
    template_path = tmp_path / "no mhc2.icm"
    output_path = tmp_path / "generated.icm"
    template_data = bytearray(make_mhc2_profile())
    template_data[144:148] = b"test"
    template_path.write_bytes(template_data)

    with pytest.raises(SystemExit) as error:
        main([str(template_path), str(output_path)])

    assert error.value.code == 2
    assert template_path.read_bytes() == template_data
    assert not output_path.exists()
