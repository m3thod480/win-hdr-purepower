"""CLI de inspección: ``python -m hdrfix.inspect perfil.icc``."""

import argparse
import json
from pathlib import Path

from .icc import ICCFormatError, ICCProfile, inspect_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hdrfix.inspect",
        description="Inspecciona un perfil ICC/ICM HDR sin modificarlo.",
    )
    parser.add_argument("profile", type=Path, help="ruta al perfil .icc o .icm")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emite el resultado completo como JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        profile = inspect_profile(arguments.profile)
    except (ICCFormatError, OSError) as error:
        parser.error(f"no se pudo inspeccionar '{arguments.profile}': {error}")

    if arguments.json:
        result = profile.to_dict()
        result["path"] = str(arguments.profile)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(arguments.profile, profile)
    return 0


def _print_human(path: Path, profile: ICCProfile) -> None:
    print(f"Perfil: {path}")
    print(f"Tamaño: {profile.file_size} bytes")
    print(f"Firma ICC: {profile.signature}")
    print(f"Etiquetas ({len(profile.tags)}):")
    for tag in profile.tags:
        print(f"  {tag.signature}  offset={tag.offset}  tamaño={tag.size}")

    if profile.mhc2 is None:
        print("MHC2: no encontrada")
        return

    mhc2 = profile.mhc2
    print("MHC2: encontrada")
    print(f"  Entradas de LUT: {mhc2.lut_entry_count}")
    print(f"  Luminancia mínima: {mhc2.min_luminance} nits")
    print(f"  Luminancia máxima: {mhc2.max_luminance} nits")
    print(f"  Offset de matriz: {mhc2.matrix_offset}")
    print(f"  Offset de LUT roja: {mhc2.red_lut_offset}")
    print(f"  Offset de LUT verde: {mhc2.green_lut_offset}")
    print(f"  Offset de LUT azul: {mhc2.blue_lut_offset}")
    print(f"  LUT roja: {json.dumps(mhc2.red_lut)}")
    print(f"  LUT verde: {json.dumps(mhc2.green_lut)}")
    print(f"  LUT azul: {json.dumps(mhc2.blue_lut)}")


if __name__ == "__main__":
    main()

