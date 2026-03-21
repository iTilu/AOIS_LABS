import pytest

from binary_int import BinaryInt


@pytest.mark.parametrize(
    "decimal_value, expected_bits",
    [
        (7, [0] * 29 + [1, 1, 1]),
        (0, [0] * 32),
    ],
)
def test_direct_inverse_additional_positive_or_zero(decimal_value, expected_bits):
    number = BinaryInt(decimal_value)
    assert number.direct_code() == expected_bits
    assert number.inverse_code() == expected_bits
    assert number.additional_code() == expected_bits


def test_direct_inverse_additional_negative():
    number = BinaryInt(-3)
    assert number.direct_code() == [1] + [0] * 28 + [0, 1, 1]
    assert number.inverse_code() == [1] + [1] * 28 + [1, 0, 0]
    assert number.additional_code() == [1] + [1] * 28 + [1, 0, 1]


def test_additional_addition():
    left_number = BinaryInt(7)
    right_number = BinaryInt(-3)
    sum_bits = left_number.add_additional(right_number)
    assert left_number.additional_to_decimal(sum_bits) == 4


def test_additional_subtraction():
    left_number = BinaryInt(7)
    right_number = BinaryInt(-3)
    difference_bits = left_number.subtract(right_number)
    assert left_number.additional_to_decimal(difference_bits) == 10


def test_negate_additional_bits():
    source_number = BinaryInt(5)
    source_bits = source_number.additional_code()
    negated_bits = source_number.negate_additional_bits(source_bits)
    assert source_number.additional_to_decimal(negated_bits) == -5


def test_direct_multiplication_sign_and_value():
    first_factor = BinaryInt(-6)
    second_factor = BinaryInt(5)
    product_bits = first_factor.multiply_direct(second_factor)
    assert first_factor.direct_to_decimal(product_bits) == -30


def test_direct_multiplication_zero():
    first_factor = BinaryInt(0)
    second_factor = BinaryInt(55)
    product_bits = first_factor.multiply_direct(second_factor)
    assert first_factor.direct_to_decimal(product_bits) == 0


def test_unsigned_divmod():
    helper_number = BinaryInt(0)
    quotient_value, remainder_value = helper_number._unsigned_divmod(20, 3)
    assert quotient_value == 6
    assert remainder_value == 2


def test_division_fixed_point_positive():
    dividend_number = BinaryInt(20)
    divisor_number = BinaryInt(3)
    quotient_bits = dividend_number.divide_direct(divisor_number, fractional_bit_count=16)

    quotient_decimal = dividend_number.direct_fixed_to_decimal(quotient_bits, fractional_bit_count=16)
    assert quotient_decimal == pytest.approx(20 / 3, abs=1e-4)

    quotient_string = dividend_number.direct_fixed_to_decimal_string(
        quotient_bits,
        precision=5,
        fractional_bit_count=16,
    )
    assert quotient_string == "6.66665"


def test_division_fixed_point_negative():
    dividend_number = BinaryInt(-20)
    divisor_number = BinaryInt(3)
    quotient_bits = dividend_number.divide_direct(divisor_number, fractional_bit_count=16)
    quotient_decimal = dividend_number.direct_fixed_to_decimal(quotient_bits, fractional_bit_count=16)
    assert quotient_decimal == pytest.approx(-20 / 3, abs=1e-4)


def test_division_by_zero():
    dividend_number = BinaryInt(5)
    divisor_number = BinaryInt(0)
    with pytest.raises(ZeroDivisionError):
        dividend_number.divide_direct(divisor_number)


def test_additional_to_decimal_negative_bits():
    number = BinaryInt(-3)
    bits = number.additional_code()
    assert number.additional_to_decimal(bits) == -3


def test_direct_to_decimal_negative_bits():
    number = BinaryInt(0)
    negative_direct_bits = [1] + [0] * 27 + [1, 1, 0, 1]
    assert number.direct_to_decimal(negative_direct_bits) == -13


def test_unsigned_divmod_with_zero_dividend_branch():
    helper_number = BinaryInt(0)
    quotient_value, remainder_value = helper_number._unsigned_divmod(0, 3)
    assert quotient_value == 0
    assert remainder_value == 0
