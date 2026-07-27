"""CLI para analizar y comparar las curvas tonales generadas."""

import argparse

from hdrfix.curve_analysis import CurveAnalysis, analyze_curves


def build_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos de terminal."""

    parser = argparse.ArgumentParser(
        prog="python -m hdrfix.analyze_curves",
        description=(
            "Compara numéricamente Pure Power de ColorControl "
            "con Smooth Anchored Power."
        ),
    )

    parser.add_argument(
        "--entries",
        type=int,
        default=1024,
        help="Número de entradas de las LUT (predeterminado: 1024).",
    )

    parser.add_argument(
        "--gamma",
        type=float,
        default=2.2,
        help="Gamma Pure Power (predeterminado: 2.2).",
    )

    parser.add_argument(
        "--sdr-white",
        type=float,
        default=100.0,
        help="Blanco SDR en nits (predeterminado: 100).",
    )

    parser.add_argument(
        "--sdr-black",
        type=float,
        default=0.0,
        help="Negro SDR en nits (predeterminado: 0).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Ejecuta el análisis y muestra el informe."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        analysis = analyze_curves(
            entries=arguments.entries,
            gamma=arguments.gamma,
            sdr_white_nits=arguments.sdr_white,
            sdr_black_nits=arguments.sdr_black,
        )
    except ValueError as error:
        parser.error(str(error))

    print_analysis(
        analysis,
        gamma=arguments.gamma,
        sdr_white_nits=arguments.sdr_white,
        sdr_black_nits=arguments.sdr_black,
    )

    return 0


def print_analysis(
    analysis: CurveAnalysis,
    *,
    gamma: float,
    sdr_white_nits: float,
    sdr_black_nits: float,
) -> None:
    """Muestra un informe legible del análisis."""

    print("Configuración:")
    print(f"  Entradas LUT: {analysis.entries}")
    print(f"  Gamma: {gamma}")
    print(f"  Negro SDR: {sdr_black_nits:.3f} nits")
    print(f"  Blanco SDR: {sdr_white_nits:.3f} nits")
    print()

    print("Muestras tonales:")
    print(
        f"{'Entrada':>10} "
        f"{'ColorControl':>14} "
        f"{'Smooth':>14} "
        f"{'Delta CC':>12} "
        f"{'Delta Smooth':>14} "
        f"{'Smooth - CC':>14}"
    )

    for sample in analysis.samples:
        print(
            f"{sample.input_nits:>10.3f} "
            f"{sample.colorcontrol_nits:>14.6f} "
            f"{sample.smooth_nits:>14.6f} "
            f"{sample.colorcontrol_delta_nits:>12.6f} "
            f"{sample.smooth_delta_nits:>14.6f} "
            f"{sample.difference_nits:>14.6f}"
        )

    print()
    print("Resumen de las LUT:")
    print(
        "  Entradas cuantizadas diferentes: "
        f"{analysis.quantized_different_entries}"
    )
    print(
        "  Smooth más brillante: "
        f"{analysis.quantized_smooth_brighter_entries}"
    )
    print(
        "  Smooth más oscura: "
        f"{analysis.quantized_smooth_darker_entries}"
    )
    print(
        "  Entradas iguales: "
        f"{analysis.quantized_equal_entries}"
    )
    print(
        "  Diferencia máxima absoluta: "
        f"{analysis.max_absolute_difference_nits:.9f} nits"
    )
    print(
        "  Diferencia máxima firmada: "
        f"{analysis.max_signed_difference_nits:.9f} nits"
    )
    print(
        "  Entrada donde ocurre: "
        f"{analysis.max_difference_input_nits:.6f} nits"
    )


if __name__ == "__main__":
    raise SystemExit(main())