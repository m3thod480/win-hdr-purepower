import pytest

from hdrfix.analyze_curves import main


def test_cli_prints_fixed_curve_analysis(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Configuración:" in output
    assert "Entradas LUT: 1024" in output
    assert "Pure Power 2.2 + Shadow Stretch" in output
    assert "Final de sombras: 10.000 nits" in output
    assert "Intensidad de sombras: 0.250" in output
    assert "Muestras tonales:" in output
    assert "Delta Pure" in output
    assert "Delta Shadow" in output
    assert "Shadow - Pure" in output
    assert "Shadow Stretch frente a Pure Power" in output
    assert "Entradas cuantizadas diferentes:" in output
    assert "Diferencia máxima:" in output
    assert "Entrada donde ocurre:" in output


def test_cli_accepts_custom_analysis_size_and_sdr_range(capsys):
    exit_code = main(
        [
            "--entries",
            "128",
            "--sdr-white",
            "80",
            "--sdr-black",
            "0",
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Entradas LUT: 128" in output
    assert "Blanco SDR: 80.000 nits" in output


@pytest.mark.parametrize(
    "removed_option",
    [
        "--gamma",
        "--shadow-end",
        "--shadow-strength",
    ],
)
def test_cli_rejects_removed_curve_options(removed_option):
    with pytest.raises(SystemExit) as error:
        main([removed_option, "1"])

    assert error.value.code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["--entries", "1"],
        ["--entries", "4097"],
        ["--sdr-white", "0"],
        ["--sdr-black", "100", "--sdr-white", "100"],
    ],
)
def test_cli_rejects_invalid_configuration(arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)

    assert error.value.code == 2
