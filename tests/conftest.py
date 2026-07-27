from collections.abc import Callable, Sequence
import struct

import pytest


def _s15_fixed_16(value: float) -> int:
    return round(value * 65_536)


def _sf32(values: Sequence[float]) -> bytes:
    return struct.pack(
        f">4sI{len(values)}i",
        b"sf32",
        0,
        *(_s15_fixed_16(value) for value in values),
    )


def _mhc2(
    red_lut: Sequence[float],
    green_lut: Sequence[float],
    blue_lut: Sequence[float],
) -> bytes:
    if not len(red_lut) == len(green_lut) == len(blue_lut):
        raise ValueError("Las tres LUT deben tener el mismo tamaño.")

    matrix_data = struct.pack(
        ">12i",
        _s15_fixed_16(1.0),
        0,
        0,
        0,
        0,
        _s15_fixed_16(1.0),
        0,
        0,
        0,
        0,
        _s15_fixed_16(1.0),
        0,
    )
    red_data = _sf32(red_lut)
    green_data = _sf32(green_lut)
    blue_data = _sf32(blue_lut)

    matrix_offset = 36
    red_offset = matrix_offset + len(matrix_data)
    green_offset = red_offset + len(red_data)
    blue_offset = green_offset + len(green_data)

    header = struct.pack(
        ">4sIIiiIIII",
        b"MHC2",
        0,
        len(red_lut),
        _s15_fixed_16(0.0),
        _s15_fixed_16(520.0),
        matrix_offset,
        red_offset,
        green_offset,
        blue_offset,
    )
    return header + matrix_data + red_data + green_data + blue_data


@pytest.fixture
def make_mhc2_profile() -> Callable[..., bytes]:
    """Construye un perfil ICC pequeño con una etiqueta MHC2 válida."""

    def factory(
        red_lut: Sequence[float] = (0.0, 1.0),
        green_lut: Sequence[float] | None = None,
        blue_lut: Sequence[float] | None = None,
    ) -> bytes:
        green_lut = red_lut if green_lut is None else green_lut
        blue_lut = red_lut if blue_lut is None else blue_lut
        mhc2_data = _mhc2(red_lut, green_lut, blue_lut)

        header = bytearray(128)
        header[4:8] = b"test"
        header[8:12] = bytes.fromhex("04300000")
        header[12:16] = b"mntr"
        header[16:20] = b"RGB "
        header[20:24] = b"XYZ "
        header[36:40] = b"acsp"
        header[44:48] = bytes.fromhex("00000001")
        header[64:68] = bytes.fromhex("00000001")
        struct.pack_into(
            ">iii",
            header,
            68,
            _s15_fixed_16(0.9642),
            _s15_fixed_16(1.0),
            _s15_fixed_16(0.8249),
        )
        header[80:84] = b"test"
        header[84:100] = bytes(range(16))

        description_data = b"test payload"
        tag_count = 2
        tag_table_end = 132 + tag_count * 12
        description_offset = tag_table_end
        mhc2_offset = description_offset + len(description_data)
        tag_table = (
            struct.pack(">I", tag_count)
            + struct.pack(
                ">4sII",
                b"desc",
                description_offset,
                len(description_data),
            )
            + struct.pack(
                ">4sII",
                b"MHC2",
                mhc2_offset,
                len(mhc2_data),
            )
        )

        result = header + tag_table + description_data + mhc2_data
        struct.pack_into(">I", result, 0, len(result))
        return bytes(result)

    return factory
