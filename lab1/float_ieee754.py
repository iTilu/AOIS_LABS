from constants import (
    BINARY_BASE,
    DECIMAL_BASE,
    IEEE754_EXPONENT_BIAS,
    IEEE754_EXPONENT_BIT_COUNT,
    IEEE754_MANTISSA_BIT_COUNT,
    IEEE754_MANTISSA_WITH_GUARD_BIT_COUNT,
    IEEE754_MAX_BIASED_EXPONENT,
    IEEE754_SUBNORMAL_EXPONENT,
    IEEE754_TOTAL_BITS,
)


class Float32:
    def __init__(self, decimal_value: float):
        self.value = decimal_value

    def _integer_to_bits(self, integer_value: int, bit_width: int):
        bit_array = [0] * bit_width
        write_position = bit_width - 1

        while integer_value > 0 and write_position >= 0:
            bit_array[write_position] = integer_value % BINARY_BASE
            integer_value //= BINARY_BASE
            write_position -= 1

        return bit_array

    def _bits_to_integer(self, bit_array):
        integer_value = 0
        for current_bit in bit_array:
            integer_value = integer_value * BINARY_BASE + current_bit
        return integer_value

    def _parse_decimal_to_ratio(self, decimal_value: float):
        decimal_text = str(decimal_value)
        sign_multiplier = 1

        if decimal_text.startswith("-"):
            sign_multiplier = -1
            decimal_text = decimal_text[1:]

        decimal_exponent = 0
        if "e" in decimal_text or "E" in decimal_text:
            exponent_parts = decimal_text.replace("E", "e").split("e")
            decimal_text = exponent_parts[0]
            decimal_exponent = int(exponent_parts[1])

        if "." in decimal_text:
            integer_part_text, fractional_part_text = decimal_text.split(".")
            combined_digits = (integer_part_text + fractional_part_text) if (integer_part_text + fractional_part_text) else "0"
            ratio_numerator = int(combined_digits)
            ratio_denominator = 1
            for _ in fractional_part_text:
                ratio_denominator *= DECIMAL_BASE
        else:
            ratio_numerator = int(decimal_text) if decimal_text else 0
            ratio_denominator = 1

        if decimal_exponent > 0:
            for _ in range(decimal_exponent):
                ratio_numerator *= DECIMAL_BASE
        elif decimal_exponent < 0:
            for _ in range(-decimal_exponent):
                ratio_denominator *= DECIMAL_BASE

        return sign_multiplier * ratio_numerator, ratio_denominator

    def _normalize_ratio(self, ratio_numerator: int, ratio_denominator: int):
        binary_exponent = 0

        while ratio_numerator >= (ratio_denominator << 1):
            ratio_denominator <<= 1
            binary_exponent += 1

        while ratio_numerator < ratio_denominator:
            ratio_numerator <<= 1
            binary_exponent -= 1

        return ratio_numerator, ratio_denominator, binary_exponent

    def _build_ieee754_bits_from_ratio(self, ratio_numerator: int, ratio_denominator: int):
        if ratio_numerator == 0:
            return [0] * IEEE754_TOTAL_BITS

        sign_bit = 1 if ratio_numerator < 0 else 0
        absolute_numerator = abs(ratio_numerator)

        normalized_numerator, normalized_denominator, binary_exponent = self._normalize_ratio(
            absolute_numerator,
            ratio_denominator,
        )

        biased_exponent_value = binary_exponent + IEEE754_EXPONENT_BIAS

        if biased_exponent_value <= 0:
            return [sign_bit] + [0] * (IEEE754_TOTAL_BITS - 1)

        if biased_exponent_value >= IEEE754_MAX_BIASED_EXPONENT:
            return [sign_bit] + [1] * IEEE754_EXPONENT_BIT_COUNT + [0] * IEEE754_MANTISSA_BIT_COUNT

        remainder_value = normalized_numerator - normalized_denominator
        mantissa_with_guard = []

        for _ in range(IEEE754_MANTISSA_WITH_GUARD_BIT_COUNT):
            remainder_value *= BINARY_BASE
            if remainder_value >= normalized_denominator:
                mantissa_with_guard.append(1)
                remainder_value -= normalized_denominator
            else:
                mantissa_with_guard.append(0)

        mantissa_bits = mantissa_with_guard[:IEEE754_MANTISSA_BIT_COUNT]
        guard_bit = mantissa_with_guard[IEEE754_MANTISSA_BIT_COUNT]

        if guard_bit == 1:
            round_position = IEEE754_MANTISSA_BIT_COUNT - 1
            while round_position >= 0 and mantissa_bits[round_position] == 1:
                mantissa_bits[round_position] = 0
                round_position -= 1

            if round_position >= 0:
                mantissa_bits[round_position] = 1
            else:
                biased_exponent_value += 1
                if biased_exponent_value >= IEEE754_MAX_BIASED_EXPONENT:
                    return [sign_bit] + [1] * IEEE754_EXPONENT_BIT_COUNT + [0] * IEEE754_MANTISSA_BIT_COUNT
                mantissa_bits = [0] * IEEE754_MANTISSA_BIT_COUNT

        exponent_bits = self._integer_to_bits(biased_exponent_value, IEEE754_EXPONENT_BIT_COUNT)
        return [sign_bit] + exponent_bits + mantissa_bits

    def to_ieee754(self):
        value_numerator, value_denominator = self._parse_decimal_to_ratio(self.value)
        return self._build_ieee754_bits_from_ratio(value_numerator, value_denominator)

    def _decode_ieee754_bits_to_ratio(self, ieee754_bits):
        sign_multiplier = -1 if ieee754_bits[0] == 1 else 1
        exponent_end = 1 + IEEE754_EXPONENT_BIT_COUNT
        exponent_value = self._bits_to_integer(ieee754_bits[1:exponent_end])
        mantissa_value = self._bits_to_integer(ieee754_bits[exponent_end:])

        if exponent_value == 0 and mantissa_value == 0:
            return 0, 1

        if exponent_value == 0:
            significand_numerator = mantissa_value
            significand_denominator = 1 << IEEE754_MANTISSA_BIT_COUNT
            exponent_shift = IEEE754_SUBNORMAL_EXPONENT
        else:
            significand_numerator = (1 << IEEE754_MANTISSA_BIT_COUNT) + mantissa_value
            significand_denominator = 1 << IEEE754_MANTISSA_BIT_COUNT
            exponent_shift = exponent_value - IEEE754_EXPONENT_BIAS

        ratio_numerator = significand_numerator
        ratio_denominator = significand_denominator

        if exponent_shift >= 0:
            ratio_numerator <<= exponent_shift
        else:
            ratio_denominator <<= -exponent_shift

        return sign_multiplier * ratio_numerator, ratio_denominator

    def _ieee754_bits_to_decimal(self, ieee754_bits):
        ratio_numerator, ratio_denominator = self._decode_ieee754_bits_to_ratio(ieee754_bits)
        return ratio_numerator / ratio_denominator

    def add(self, other_number):
        left_numerator, left_denominator = self._decode_ieee754_bits_to_ratio(self.to_ieee754())
        right_numerator, right_denominator = self._decode_ieee754_bits_to_ratio(other_number.to_ieee754())

        result_numerator = left_numerator * right_denominator + right_numerator * left_denominator
        result_denominator = left_denominator * right_denominator

        return self._build_ieee754_bits_from_ratio(result_numerator, result_denominator)

    def subtract(self, other_number):
        left_numerator, left_denominator = self._decode_ieee754_bits_to_ratio(self.to_ieee754())
        right_numerator, right_denominator = self._decode_ieee754_bits_to_ratio(other_number.to_ieee754())

        result_numerator = left_numerator * right_denominator - right_numerator * left_denominator
        result_denominator = left_denominator * right_denominator

        return self._build_ieee754_bits_from_ratio(result_numerator, result_denominator)

    def multiply(self, other_number):
        left_numerator, left_denominator = self._decode_ieee754_bits_to_ratio(self.to_ieee754())
        right_numerator, right_denominator = self._decode_ieee754_bits_to_ratio(other_number.to_ieee754())

        result_numerator = left_numerator * right_numerator
        result_denominator = left_denominator * right_denominator

        return self._build_ieee754_bits_from_ratio(result_numerator, result_denominator)

    def divide(self, other_number):
        left_numerator, left_denominator = self._decode_ieee754_bits_to_ratio(self.to_ieee754())
        right_numerator, right_denominator = self._decode_ieee754_bits_to_ratio(other_number.to_ieee754())

        if right_numerator == 0:
            raise ZeroDivisionError("float division by zero")

        result_numerator = left_numerator * right_denominator
        result_denominator = left_denominator * right_numerator

        return self._build_ieee754_bits_from_ratio(result_numerator, result_denominator)

    def ieee_bits_to_decimal(self, ieee754_bits):
        return self._ieee754_bits_to_decimal(ieee754_bits)
