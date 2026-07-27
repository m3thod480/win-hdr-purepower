"""CLI para generar un perfil ICC/MHC2 parcheado."""

import argparse
import math
import os
from pathlib import Path
import tempfile

from hdrfix.curves import (
    PURE_POWER_GAMMA,
    SHADOW_STRETCH_END_NITS,
    SHADOW_STRETCH_STRENGTH,
    generate_shadow_stretch_lut,
)
from hdrfix.icc import ICCFormatError, parse_profile
from hdrfix.profile_patcher import (
    ICC_PROFILE_ID_OFFSET,
    ICC_PROFILE_ID_SIZE,
    build_patched_profile,
)


def build_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos de terminal."""

    parser = argparse.ArgumentParser(
        prog="python -m hdrfix.generate_profile",
        description=(
            "Genera un perfil ICC/ICM HDR con Pure Power 2.2 "
            "y Shadow Stretch fijo, sustituyendo las LUT MHC2 "
            "de una plantilla."
        ),
    )
    parser.add_argument(
        "template",
        type=Path,
        help="Perfil ICC/ICM usado como plantilla.",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Ruta del nuevo perfil ICC/ICM.",
    )
    parser.add_argument(
        "--sdr-white",
        dest="sdr_white",
        type=float,
        default=100.0,
        help="Blanco SDR en nits (predeterminado: 100).",
    )
    parser.add_argument(
        "--sdr-black",
        dest="sdr_black",
        type=float,
        default=0.0,
        help="Negro SDR en nits (predeterminado: 0).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Permite sustituir un archivo de salida existente.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Genera, escribe y verifica un perfil ICC/ICM parcheado."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        paths_match = _paths_refer_to_same_file(
            arguments.template,
            arguments.output,
        )
        output_exists = arguments.output.exists()
    except (OSError, RuntimeError) as error:
        parser.error(f"no se pudieron validar las rutas: {error}")

    if paths_match:
        parser.error(
            "la plantilla y el archivo de salida deben ser rutas distintas"
        )

    if output_exists and not arguments.force:
        parser.error(
            f"el archivo de salida ya existe: '{arguments.output}'; "
            "use --force para sustituirlo"
        )

    try:
        template_data = arguments.template.read_bytes()
        template_profile = parse_profile(template_data)

        if template_profile.mhc2 is None:
            raise ValueError(
                "La plantilla no contiene una etiqueta MHC2."
            )

        entries = template_profile.mhc2.lut_entry_count

        _validate_generation_parameters(
            entries=entries,
            sdr_white_nits=arguments.sdr_white,
            sdr_black_nits=arguments.sdr_black,
        )

        lut = generate_shadow_stretch_lut(
            entries=entries,
            sdr_white_nits=arguments.sdr_white,
            sdr_black_nits=arguments.sdr_black,
        )
        final_data = build_patched_profile(template_data, lut)

        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        _write_profile_atomically(
            arguments.output,
            final_data,
            force=arguments.force,
        )

        written_data = arguments.output.read_bytes()
        parse_profile(written_data)
    except FileExistsError:
        parser.error(
            f"el archivo de salida ya existe: '{arguments.output}'; "
            "use --force para sustituirlo"
        )
    except (ICCFormatError, OSError, ValueError) as error:
        parser.error(f"no se pudo generar el perfil: {error}")

    profile_id = written_data[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ]
    _print_summary(
        entries=entries,
        sdr_white_nits=arguments.sdr_white,
        sdr_black_nits=arguments.sdr_black,
        output_path=arguments.output,
        profile_id=profile_id,
    )
    return 0


def _validate_generation_parameters(
    *,
    entries: int,
    sdr_white_nits: float,
    sdr_black_nits: float,
) -> None:
    if entries != 1024:
        raise ValueError(
            f"Detected {entries} MHC2 LUT entries. "
            "Windows HDR Shadow Stretch v0.1 requires "
            "a 1024-entry MHC2 template; two-entry Windows HDR "
            "Calibration identity profiles are unsuitable."
        )
    if not (
        math.isfinite(sdr_black_nits)
        and math.isfinite(sdr_white_nits)
        and 0.0 <= sdr_black_nits
        < sdr_white_nits
        <= 10_000.0
    ):
        raise ValueError(
            "El rango SDR debe ser finito, estar entre 0 y 10.000 nits "
            "y el blanco debe superar al negro."
        )
    if sdr_white_nits < SHADOW_STRETCH_END_NITS:
        raise ValueError(
            "El blanco SDR no puede ser inferior al final fijo "
            f"de sombras ({SHADOW_STRETCH_END_NITS} nits)."
        )


def _paths_refer_to_same_file(left: Path, right: Path) -> bool:
    if left.resolve(strict=False) == right.resolve(strict=False):
        return True

    try:
        return left.samefile(right)
    except OSError:
        return False


def _write_profile_atomically(
    path: Path,
    profile_data: bytes,
    *,
    force: bool,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(profile_data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if force:
            os.replace(temporary_path, path)
        else:
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                raise
            except OSError:
                _write_profile_exclusively(path, profile_data)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _write_profile_exclusively(
    path: Path,
    profile_data: bytes,
) -> None:
    output_file = path.open("xb")

    try:
        with output_file:
            output_file.write(profile_data)
            output_file.flush()
            os.fsync(output_file.fileno())
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _print_summary(
    *,
    entries: int,
    sdr_white_nits: float,
    sdr_black_nits: float,
    output_path: Path,
    profile_id: bytes,
) -> None:
    print("Perfil generado:")
    print(f"  Curve: Pure Power {PURE_POWER_GAMMA} + Shadow Stretch")
    print(f"  Shadow end: {SHADOW_STRETCH_END_NITS} nits")
    print(f"  Shadow strength: {SHADOW_STRETCH_STRENGTH}")
    print(f"  Entradas: {entries}")
    print(f"  Negro SDR: {sdr_black_nits} nits")
    print(f"  Blanco SDR: {sdr_white_nits} nits")
    print(f"  Salida: {output_path}")
    print(f"  Profile ID: {profile_id.hex()}")


if __name__ == "__main__":
    raise SystemExit(main())
