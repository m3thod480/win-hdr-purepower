"""CLI para analizar la curva tonal final."""

import argparse

from hdrfix.curve_analysis import CurveAnalysis, analyze_curves
from hdrfix.curves import (
    PURE_POWER_GAMMA,
    SHADOW_STRETCH_END_NITS,
    SHADOW_STRETCH_STRENGTH,
)


def build_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos de terminal."""

    parser = argparse.ArgumentParser(
        prog="python -m hdrfix.analyze_curves",
        description=(
            "Compara numéricamente Pure Power 2.2 con la curva final "
            "de Shadow Stretch fijo."
        ),
    )
    parser.add_argument(
        "--entries",
        type=int,
        default=1024,
        help="Número de entradas de las LUT (predeterminado: 1024).",
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
            sdr_white_nits=arguments.sdr_white,
            sdr_black_nits=arguments.sdr_black,
        )
    except ValueError as error:
        parser.error(str(error))

    print_analysis(
        analysis,
        sdr_white_nits=arguments.sdr_white,
        sdr_black_nits=arguments.sdr_black,
    )
    return 0


def print_analysis(
    analysis: CurveAnalysis,
    *,
    sdr_white_nits: float,
    sdr_black_nits: float,
) -> None:
    """Muestra un informe legible del análisis."""

    print("Configuración:")
    print(f"  Entradas LUT: {analysis.entries}")
    print(
        "  Curva: "
        f"Pure Power {PURE_POWER_GAMMA} + Shadow Stretch"
    )
    print(f"  Negro SDR: {sdr_black_nits:.3f} nits")
    print(f"  Blanco SDR: {sdr_white_nits:.3f} nits")
    print(
        "  Final de sombras: "
        f"{SHADOW_STRETCH_END_NITS:.3f} nits"
    )
    print(
        "  Intensidad de sombras: "
        f"{SHADOW_STRETCH_STRENGTH:.3f}"
    )
    print()

    print("Muestras tonales:")
    print(
        f"{'Entrada':>10} "
        f"{'Pure Power':>14} "
        f"{'Shadow Stretch':>16} "
        f"{'Delta Pure':>12} "
        f"{'Delta Shadow':>14} "
        f"{'Shadow - Pure':>14}"
    )
    for sample in analysis.samples:
        print(
            f"{sample.input_nits:>10.3f} "
            f"{sample.pure_power_nits:>14.6f} "
            f"{sample.shadow_stretch_nits:>16.6f} "
            f"{sample.pure_power_delta_nits:>12.6f} "
            f"{sample.shadow_stretch_delta_nits:>14.6f} "
            f"{sample.shadow_stretch_minus_pure_power_nits:>14.6f}"
        )

    print()
    print("Resumen de las LUT:")
    print("  Shadow Stretch frente a Pure Power:")
    print(
        "  Entradas cuantizadas diferentes: "
        f"{analysis.quantized_different_entries}"
    )
    print(
        "  Diferencia máxima: "
        f"{analysis.max_difference_nits:.9f} nits"
    )
    print(
        "  Entrada donde ocurre: "
        f"{analysis.max_difference_input_nits:.6f} nits"
    )


if __name__ == "__main__":
    raise SystemExit(main())
