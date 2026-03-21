import pytest

from float_ieee754 import Float32


def test_to_ieee754_known_value_575():
    number = Float32(5.75)
    bits = number.to_ieee754()
    assert bits == [0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def test_to_ieee754_zero():
    number = Float32(0.0)
    bits = number.to_ieee754()
    assert bits == [0] * 32


def test_to_ieee754_negative():
    number = Float32(-2.5)
    bits = number.to_ieee754()
    assert bits[0] == 1


def test_ieee_bits_to_decimal_roundtrip():
    source_value = 2.5
    number = Float32(source_value)
    bits = number.to_ieee754()
    decoded_value = number.ieee_bits_to_decimal(bits)
    assert decoded_value == pytest.approx(source_value, abs=1e-6)


def test_add():
    left_number = Float32(5.75)
    right_number = Float32(2.5)
    sum_bits = left_number.add(right_number)
    assert left_number.ieee_bits_to_decimal(sum_bits) == pytest.approx(8.25, abs=1e-6)


def test_subtract():
    left_number = Float32(5.75)
    right_number = Float32(2.5)
    difference_bits = left_number.subtract(right_number)
    assert left_number.ieee_bits_to_decimal(difference_bits) == pytest.approx(3.25, abs=1e-6)


def test_multiply():
    left_number = Float32(5.75)
    right_number = Float32(2.5)
    product_bits = left_number.multiply(right_number)
    assert left_number.ieee_bits_to_decimal(product_bits) == pytest.approx(14.375, abs=1e-6)


def test_divide():
    left_number = Float32(5.75)
    right_number = Float32(2.5)
    quotient_bits = left_number.divide(right_number)
    assert left_number.ieee_bits_to_decimal(quotient_bits) == pytest.approx(2.3, abs=1e-6)


def test_divide_by_zero():
    left_number = Float32(5.75)
    right_number = Float32(0.0)
    with pytest.raises(ZeroDivisionError):
        left_number.divide(right_number)


def test_add_negative_numbers():
    left_number = Float32(-1.5)
    right_number = Float32(-2.25)
    sum_bits = left_number.add(right_number)
    assert left_number.ieee_bits_to_decimal(sum_bits) == pytest.approx(-3.75, abs=1e-6)


def test_parse_decimal_to_ratio_with_scientific_notation_positive_exponent():
    number = Float32(0.0)
    ratio_numerator, ratio_denominator = number._parse_decimal_to_ratio(1e20)
    assert ratio_numerator == 10 ** 20
    assert ratio_denominator == 1


def test_parse_decimal_to_ratio_with_scientific_notation_negative_exponent():
    number = Float32(0.0)
    ratio_numerator, ratio_denominator = number._parse_decimal_to_ratio(1e-20)
    assert ratio_numerator == 1
    assert ratio_denominator == 10 ** 20


def test_parse_decimal_to_ratio_without_fractional_part_branch():
    number = Float32(0.0)
    ratio_numerator, ratio_denominator = number._parse_decimal_to_ratio(42)
    assert ratio_numerator == 42
    assert ratio_denominator == 1


def test_normalize_ratio_when_numerator_less_than_denominator():
    number = Float32(0.0)
    normalized_numerator, normalized_denominator, binary_exponent = number._normalize_ratio(1, 2)
    assert normalized_numerator == 2
    assert normalized_denominator == 2
    assert binary_exponent == -1


def test_build_ieee754_underflow_branch():
    number = Float32(0.0)
    bits = number._build_ieee754_bits_from_ratio(1, 1 << 300)
    assert bits == [0] * 32


def test_build_ieee754_overflow_branch():
    number = Float32(0.0)
    bits = number._build_ieee754_bits_from_ratio(1 << 300, 1)
    assert bits == [0] + [1] * 8 + [0] * 23


def test_build_ieee754_rounding_with_mantissa_overflow_without_exponent_overflow():
    number = Float32(0.0)
    source_denominator = 1 << 30
    source_numerator = (source_denominator << 1) - 1
    bits = number._build_ieee754_bits_from_ratio(source_numerator, source_denominator)
    assert bits[0] == 0
    assert bits[1:9] == [1, 0, 0, 0, 0, 0, 0, 0]
    assert bits[9:] == [0] * 23


def test_build_ieee754_rounding_with_exponent_overflow():
    number = Float32(0.0)
    source_numerator = (1 << 128) - 1
    source_denominator = 1
    bits = number._build_ieee754_bits_from_ratio(source_numerator, source_denominator)
    assert bits == [0] + [1] * 8 + [0] * 23


def test_build_ieee754_rounding_with_carry_without_full_mantissa_reset():
    number = Float32(0.0)
    source_numerator = (1 << 24) + 1
    source_denominator = 1 << 24
    bits = number._build_ieee754_bits_from_ratio(source_numerator, source_denominator)
    assert bits[0] == 0
    assert bits[1:9] == [0, 1, 1, 1, 1, 1, 1, 1]
    assert bits[9:] == [0] * 22 + [1]


def test_decode_subnormal_number_branch():
    number = Float32(0.0)
    subnormal_bits = [0] + [0] * 8 + [0] * 22 + [1]
    ratio_numerator, ratio_denominator = number._decode_ieee754_bits_to_ratio(subnormal_bits)
    assert ratio_numerator == 1
    assert ratio_denominator == (1 << 149)


def test_decode_normal_number_with_negative_exponent_shift_branch():
    number = Float32(0.0)
    half_bits = Float32(0.5).to_ieee754()
    ratio_numerator, ratio_denominator = number._decode_ieee754_bits_to_ratio(half_bits)
    assert ratio_numerator == (1 << 23)
    assert ratio_denominator == (1 << 24)
    assert ratio_numerator / ratio_denominator == pytest.approx(0.5, abs=1e-12)
