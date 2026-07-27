"""Modificación controlada de las LUT de un perfil ICC/MHC2."""

from collections.abc import Sequence
import math
import struct

from hdrfix.curves import quantize_s15_fixed_16
from hdrfix.icc import SF32_HEADER_SIZE, parse_profile


ICC_PROFILE_ID_OFFSET = 84
ICC_PROFILE_ID_SIZE = 16


def replace_mhc2_luts(
    profile_data: bytes,
    lut: Sequence[float],
) -> bytes:
    """Devuelve una copia del perfil con las tres LUT MHC2 sustituidas."""

    profile = parse_profile(profile_data)

    if profile.mhc2 is None:
        raise ValueError("El perfil no contiene una etiqueta MHC2.")

    expected_entries = profile.mhc2.lut_entry_count

    if len(lut) != expected_entries:
        raise ValueError(
            "La LUT nueva debe tener el mismo número de entradas "
            f"que el perfil: esperadas {expected_entries}, recibidas {len(lut)}."
        )

    if any(
        not math.isfinite(value) or not 0.0 <= value <= 1.0
        for value in lut
    ):
        raise ValueError(
            "Todas las entradas de la LUT deben ser finitas "
            "y estar entre 0 y 1."
        )

    mhc2_tag = next(
        tag for tag in profile.tags
        if tag.signature == "MHC2"
    )

    quantized = tuple(
        quantize_s15_fixed_16(value)
        for value in lut
    )

    packed_lut = struct.pack(
        f">{len(quantized)}i",
        *quantized,
    )

    result = bytearray(profile_data)

    for relative_offset in (
        profile.mhc2.red_lut_offset,
        profile.mhc2.green_lut_offset,
        profile.mhc2.blue_lut_offset,
    ):
        values_start = (
            mhc2_tag.offset
            + relative_offset
            + SF32_HEADER_SIZE
        )

        values_end = values_start + len(packed_lut)

        result[values_start:values_end] = packed_lut

    # Los datos del perfil han cambiado. Dejamos el Profile ID sin calcular.
    result[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] = bytes(ICC_PROFILE_ID_SIZE)

    return bytes(result)