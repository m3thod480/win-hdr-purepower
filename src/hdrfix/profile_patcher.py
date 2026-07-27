"""Modificación controlada de las LUT de un perfil ICC/MHC2."""

from collections.abc import Sequence
import hashlib
import math
import struct

from hdrfix.curves import quantize_s15_fixed_16
from hdrfix.icc import (
    ICCFormatError,
    ICCProfile,
    SF32_HEADER_SIZE,
    parse_profile,
)


ICC_PROFILE_SIZE_OFFSET = 0
ICC_PROFILE_FLAGS_OFFSET = 44
ICC_RENDERING_INTENT_OFFSET = 64
ICC_PROFILE_ID_OFFSET = 84
ICC_PROFILE_ID_SIZE = 16
ICC_UINT32_SIZE = 4


def calculate_profile_id(profile_data: bytes) -> bytes:
    """Calcula el Profile ID MD5 definido por la especificación ICC."""

    _parse_sized_profile(profile_data)
    normalized_data = bytearray(profile_data)

    normalized_data[
        ICC_PROFILE_FLAGS_OFFSET:
        ICC_PROFILE_FLAGS_OFFSET + ICC_UINT32_SIZE
    ] = bytes(ICC_UINT32_SIZE)
    normalized_data[
        ICC_RENDERING_INTENT_OFFSET:
        ICC_RENDERING_INTENT_OFFSET + ICC_UINT32_SIZE
    ] = bytes(ICC_UINT32_SIZE)
    normalized_data[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] = bytes(ICC_PROFILE_ID_SIZE)

    return hashlib.md5(
        normalized_data,
        usedforsecurity=False,
    ).digest()


def set_profile_id(profile_data: bytes) -> bytes:
    """Devuelve una copia con su Profile ID calculado e insertado."""

    profile_id = calculate_profile_id(profile_data)
    result = bytearray(profile_data)
    result[
        ICC_PROFILE_ID_OFFSET:
        ICC_PROFILE_ID_OFFSET + ICC_PROFILE_ID_SIZE
    ] = profile_id
    return bytes(result)


def replace_mhc2_luts(
    profile_data: bytes,
    lut: Sequence[float],
) -> bytes:
    """Devuelve una copia del perfil con las tres LUT MHC2 sustituidas."""

    profile = _parse_sized_profile(profile_data)

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


def build_patched_profile(
    template_profile_data: bytes,
    lut: Sequence[float],
) -> bytes:
    """Construye y valida un perfil con las LUT y el Profile ID nuevos."""

    patched_data = replace_mhc2_luts(
        template_profile_data,
        lut,
    )
    final_data = set_profile_id(patched_data)
    _parse_sized_profile(final_data)
    return final_data


def _parse_sized_profile(profile_data: bytes) -> ICCProfile:
    """Valida la estructura y el tamaño declarado de un perfil."""

    profile = parse_profile(profile_data)
    declared_size = struct.unpack_from(
        ">I",
        profile_data,
        ICC_PROFILE_SIZE_OFFSET,
    )[0]

    if declared_size != len(profile_data):
        raise ICCFormatError(
            "El tamaño declarado del perfil ICC no coincide con sus datos: "
            f"declara {declared_size} bytes y contiene {len(profile_data)}."
        )

    return profile
