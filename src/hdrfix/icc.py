"""Parser binario, acotado y de solo lectura para la parte ICC/MHC2."""

from dataclasses import dataclass
from pathlib import Path
import struct


ICC_MINIMUM_SIZE = 132
ICC_HEADER_SIGNATURE_OFFSET = 36
ICC_TAG_COUNT_OFFSET = 128
ICC_TAG_TABLE_OFFSET = 132
ICC_TAG_ENTRY_SIZE = 12
MHC2_HEADER_SIZE = 36
MHC2_MAX_LUT_ENTRIES = 4096
SF32_HEADER_SIZE = 8
S15_FIXED_16_SCALE = 65536.0


class ICCFormatError(ValueError):
    """Indica que los bytes no forman la estructura ICC/MHC2 esperada."""


@dataclass(frozen=True)
class ICCTag:
    """Una entrada de la tabla de etiquetas ICC."""

    signature: str
    offset: int
    size: int

    def to_dict(self) -> dict:
        return {
            "signature": self.signature,
            "offset": self.offset,
            "size": self.size,
        }


@dataclass(frozen=True)
class MHC2Tag:
    """Cabecera MHC2 y sus tres LUT decodificadas."""

    lut_entry_count: int
    min_luminance: float
    max_luminance: float
    matrix_offset: int
    red_lut_offset: int
    green_lut_offset: int
    blue_lut_offset: int
    red_lut: tuple[float, ...]
    green_lut: tuple[float, ...]
    blue_lut: tuple[float, ...]

    def to_dict(self) -> dict:
        return {
            "lut_entry_count": self.lut_entry_count,
            "min_luminance": self.min_luminance,
            "max_luminance": self.max_luminance,
            "matrix_offset": self.matrix_offset,
            "red_lut_offset": self.red_lut_offset,
            "green_lut_offset": self.green_lut_offset,
            "blue_lut_offset": self.blue_lut_offset,
            "red_lut": list(self.red_lut),
            "green_lut": list(self.green_lut),
            "blue_lut": list(self.blue_lut),
        }


@dataclass(frozen=True)
class ICCProfile:
    """Resultado inmutable de inspeccionar un perfil ICC."""

    file_size: int
    signature: str
    tags: tuple[ICCTag, ...]
    mhc2: MHC2Tag | None

    def to_dict(self) -> dict:
        return {
            "file_size": self.file_size,
            "signature": self.signature,
            "tags": [tag.to_dict() for tag in self.tags],
            "mhc2": None if self.mhc2 is None else self.mhc2.to_dict(),
        }


def read_profile(path: str | Path) -> bytes:
    """Abre *path* en modo binario y devuelve una copia de sus bytes."""

    return Path(path).read_bytes()


def parse_profile(data: bytes) -> ICCProfile:
    """Valida y analiza los campos ICC y MHC2 requeridos por el inspector."""

    if len(data) < ICC_MINIMUM_SIZE:
        raise ICCFormatError(
            "Perfil ICC demasiado corto: se requieren al menos "
            f"{ICC_MINIMUM_SIZE} bytes y solo hay {len(data)}."
        )

    header_signature = data[
        ICC_HEADER_SIGNATURE_OFFSET : ICC_HEADER_SIGNATURE_OFFSET + 4
    ]
    if header_signature != b"acsp":
        raise ICCFormatError(
            "Firma ICC inválida en los bytes 36-39: "
            f"se esperaba 'acsp' y se encontró {_display_signature(header_signature)}."
        )

    tag_count = struct.unpack_from(">I", data, ICC_TAG_COUNT_OFFSET)[0]
    tag_table_size = tag_count * ICC_TAG_ENTRY_SIZE
    available_table_bytes = len(data) - ICC_TAG_TABLE_OFFSET
    if tag_table_size > available_table_bytes:
        raise ICCFormatError(
            "Tabla de etiquetas ICC truncada: "
            f"declara {tag_count} entradas ({tag_table_size} bytes), pero desde "
            f"el byte {ICC_TAG_TABLE_OFFSET} solo hay {available_table_bytes}."
        )

    tags = []
    for index in range(tag_count):
        entry_offset = ICC_TAG_TABLE_OFFSET + index * ICC_TAG_ENTRY_SIZE
        raw_signature, offset, size = struct.unpack_from(">4sII", data, entry_offset)
        try:
            signature = raw_signature.decode("ascii")
        except UnicodeDecodeError as error:
            raise ICCFormatError(
                f"La firma de la etiqueta #{index} no contiene cuatro bytes ASCII: "
                f"{raw_signature.hex()}."
            ) from error

        if offset > len(data) or size > len(data) - offset:
            raise ICCFormatError(
                f"La etiqueta '{signature}' #{index} queda fuera del archivo: "
                f"offset={offset}, tamaño={size}, archivo={len(data)} bytes."
            )
        tags.append(ICCTag(signature=signature, offset=offset, size=size))

    mhc2_entry = next((tag for tag in tags if tag.signature == "MHC2"), None)
    mhc2 = None if mhc2_entry is None else _parse_mhc2(data, mhc2_entry)

    return ICCProfile(
        file_size=len(data),
        signature="acsp",
        tags=tuple(tags),
        mhc2=mhc2,
    )


def inspect_profile(path: str | Path) -> ICCProfile:
    """Lee y analiza un perfil sin escribir en él ni en ningún otro archivo."""

    return parse_profile(read_profile(path))


def _parse_mhc2(data: bytes, tag: ICCTag) -> MHC2Tag:
    if tag.size < MHC2_HEADER_SIZE:
        raise ICCFormatError(
            "Etiqueta MHC2 truncada: "
            f"se requieren al menos {MHC2_HEADER_SIZE} bytes y declara {tag.size}."
        )

    payload = data[tag.offset : tag.offset + tag.size]
    (
        type_signature,
        reserved,
        lut_entry_count,
        min_luminance_raw,
        max_luminance_raw,
        matrix_offset,
        red_lut_offset,
        green_lut_offset,
        blue_lut_offset,
    ) = struct.unpack_from(">4sIIiiIIII", payload, 0)

    if type_signature != b"MHC2":
        raise ICCFormatError(
            "Firma interna de MHC2 inválida: "
            f"se esperaba 'MHC2' y se encontró {_display_signature(type_signature)}."
        )
    if reserved != 0:
        raise ICCFormatError(
            f"Campo reservado de MHC2 inválido: se esperaba 0 y vale {reserved}."
        )
    if lut_entry_count > MHC2_MAX_LUT_ENTRIES:
        raise ICCFormatError(
            "Número de entradas de LUT MHC2 inválido: "
            f"{lut_entry_count}; el máximo admitido es {MHC2_MAX_LUT_ENTRIES}."
        )

    if lut_entry_count == 0:
        red_lut = ()
        green_lut = ()
        blue_lut = ()
    else:
        red_lut = _read_sf32_lut(
            payload, red_lut_offset, lut_entry_count, "roja"
        )
        green_lut = _read_sf32_lut(
            payload, green_lut_offset, lut_entry_count, "verde"
        )
        blue_lut = _read_sf32_lut(
            payload, blue_lut_offset, lut_entry_count, "azul"
        )

    return MHC2Tag(
        lut_entry_count=lut_entry_count,
        min_luminance=min_luminance_raw / S15_FIXED_16_SCALE,
        max_luminance=max_luminance_raw / S15_FIXED_16_SCALE,
        matrix_offset=matrix_offset,
        red_lut_offset=red_lut_offset,
        green_lut_offset=green_lut_offset,
        blue_lut_offset=blue_lut_offset,
        red_lut=red_lut,
        green_lut=green_lut,
        blue_lut=blue_lut,
    )


def _read_sf32_lut(
    mhc2_payload: bytes, offset: int, entry_count: int, channel: str
) -> tuple[float, ...]:
    if offset < MHC2_HEADER_SIZE:
        raise ICCFormatError(
            f"Offset de la LUT {channel} de MHC2 inválido: {offset}; "
            f"debe ser al menos {MHC2_HEADER_SIZE}."
        )

    required_size = SF32_HEADER_SIZE + entry_count * 4
    if offset > len(mhc2_payload) or required_size > len(mhc2_payload) - offset:
        raise ICCFormatError(
            f"LUT {channel} de MHC2 fuera de límites: offset relativo={offset}, "
            f"tamaño necesario={required_size}, etiqueta={len(mhc2_payload)} bytes."
        )

    type_signature, reserved = struct.unpack_from(">4sI", mhc2_payload, offset)
    if type_signature != b"sf32":
        raise ICCFormatError(
            f"Firma de la LUT {channel} inválida en el offset relativo {offset}: "
            f"se esperaba 'sf32' y se encontró {_display_signature(type_signature)}."
        )
    if reserved != 0:
        raise ICCFormatError(
            f"Campo reservado de la LUT {channel} inválido en el offset relativo "
            f"{offset}: se esperaba 0 y vale {reserved}."
        )

    raw_values = struct.unpack_from(
        f">{entry_count}i", mhc2_payload, offset + SF32_HEADER_SIZE
    )
    return tuple(value / S15_FIXED_16_SCALE for value in raw_values)


def _display_signature(signature: bytes) -> str:
    try:
        return repr(signature.decode("ascii"))
    except UnicodeDecodeError:
        return f"0x{signature.hex()}"
