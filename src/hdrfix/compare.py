"""CLI para comparar las curvas MHC2 de dos perfiles ICC HDR."""

import argparse
from pathlib import Path

from .comparison import ToneCurveComparison, compare_profiles
from .icc import ICCFormatError, inspect_profile


def build_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos de la terminal."""
    parser = argparse.ArgumentParser(
        prog="python -m hdrfix.compare",
        description=(
            "Compara la información tonal MHC2 de dos perfiles "
            "ICC/ICM sin modificarlos."
        ),
    )

    parser.add_argument(
        "left",
        type=Path,
        help="ruta al primer perfil ICC/ICM",
    )

    parser.add_argument(
        "right",
        type=Path,
        help="ruta al segundo perfil ICC/ICM",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Inspecciona y compara dos perfiles sin modificarlos."""
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        left_profile = inspect_profile(arguments.left)
    except (ICCFormatError, OSError) as error:
        parser.error(f"no se pudo inspeccionar '{arguments.left}': {error}")

    try:
        right_profile = inspect_profile(arguments.right)
    except (ICCFormatError, OSError) as error:
        parser.error(f"no se pudo inspeccionar '{arguments.right}': {error}")

    comparison = compare_profiles(left_profile, right_profile)
    _print_human(arguments.left, arguments.right, comparison)
    return 0


def _print_human(
    left_path: Path,
    right_path: Path,
    comparison: ToneCurveComparison,
) -> None:
    """Muestra los resúmenes de ambos perfiles y su comparación."""
    profiles = (
        ("Perfil izquierdo", left_path, comparison.left),
        ("Perfil derecho", right_path, comparison.right),
    )

    for index, (label, path, summary) in enumerate(profiles):
        if index:
            print()
        print(f"{label}: {path}")
        print(f"  MHC2: {_display_value(summary.has_mhc2)}")
        print(
            "  Luminancia mínima: "
            f"{_display_value(summary.min_luminance)}"
        )
        print(
            "  Luminancia máxima: "
            f"{_display_value(summary.max_luminance)}"
        )
        print(
            "  Número de entradas de LUT: "
            f"{_display_value(summary.lut_entry_count)}"
        )
        print(
            "  Canales RGB iguales: "
            f"{_display_value(summary.rgb_channels_equal)}"
        )
        print(
            "  LUT de identidad: "
            f"{_display_value(summary.is_identity)}"
        )

    print()
    print("Comparación:")
    print(
        "  Misma luminancia mínima: "
        f"{_display_value(comparison.same_min_luminance)}"
    )
    print(
        "  Misma luminancia máxima: "
        f"{_display_value(comparison.same_max_luminance)}"
    )
    print(
        "  Mismo número de entradas de LUT: "
        f"{_display_value(comparison.same_lut_entry_count)}"
    )
    print(
        "  Mismo estado de identidad: "
        f"{_display_value(comparison.same_identity_status)}"
    )


def _display_value(value: bool | float | int | None) -> str:
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    if value is None:
        return "No disponible"
    return str(value)


if __name__ == "__main__":
    main()
