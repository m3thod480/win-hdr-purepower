import pytest

from hdrfix.analyze_curves import main


def test_cli_prints_curve_analysis(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Configuración:" in output
    assert "Entradas LUT: 1024" in output
    assert "Muestras tonales:" in output
    assert "ColorControl" in output
    assert "Smooth" in output
    assert "Resumen de las LUT:" in output
    assert "Entradas cuantizadas diferentes:" in output
    assert "Diferencia máxima absoluta:" in output


def test_cli_accepts_custom_configuration(capsys):
    exit_code = main(
        [
            "--entries",
            "128",
            "--gamma",
            "2.4",
            "--sdr-white",
            "80",
            "--sdr-black",
            "0",
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Entradas LUT: 128" in output
    assert "Gamma: 2.4" in output
    assert "Blanco SDR: 80.000 nits" in output


@pytest.mark.parametrize(
    "arguments",
    [
        ["--entries", "1"],
        ["--entries", "4097"],
        ["--gamma", "0"],
        ["--sdr-white", "0"],
        ["--sdr-black", "100", "--sdr-white", "100"],
    ],
)
def test_cli_rejects_invalid_configuration(arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)

    assert error.value.code == 2