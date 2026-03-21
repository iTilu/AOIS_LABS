import pytest

from bcd_excess3 import Excess3BCD


def test_int_to_bits():
    codec = Excess3BCD()
    assert codec.int_to_bits(11, 4) == [1, 0, 1, 1]


def test_bits_to_int():
    codec = Excess3BCD()
    assert codec.bits_to_int([1, 0, 1, 1]) == 11


def test_encode_decode_digit():
    codec = Excess3BCD()
    encoded_bits = codec.encode_digit(5)
    assert encoded_bits == [1, 0, 0, 0]
    assert codec.decode_digit(encoded_bits) == 5


def test_encode_decode_number():
    codec = Excess3BCD()
    encoded_bits = codec.encode_number(121)
    assert encoded_bits == [0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0]
    assert codec.decode_number(encoded_bits) == 121


def test_encode_zero():
    codec = Excess3BCD()
    encoded_bits = codec.encode_number(0)
    assert encoded_bits == [0, 0, 1, 1]
    assert codec.decode_number(encoded_bits) == 0


def test_encode_negative_raises():
    codec = Excess3BCD()
    with pytest.raises(ValueError):
        codec.encode_number(-1)


def test_decode_invalid_length_raises():
    codec = Excess3BCD()
    with pytest.raises(ValueError):
        codec.decode_number([1, 0, 1])


def test_decode_invalid_digit_raises():
    codec = Excess3BCD()
    with pytest.raises(ValueError):
        codec.decode_number([0, 0, 0, 0])


def test_add():
    codec = Excess3BCD()
    sum_bits = codec.add(121, 86)
    assert codec.decode_number(sum_bits) == 207


def test_add_with_carry_block():
    codec = Excess3BCD()
    sum_bits = codec.add(999, 1)
    assert codec.decode_number(sum_bits) == 1000


def test_add_with_left_padding_branch():
    codec = Excess3BCD()
    sum_bits = codec.add(9, 10)
    assert codec.decode_number(sum_bits) == 19
