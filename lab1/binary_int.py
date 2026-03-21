class BinaryInt:
    def __init__(self, decimal_value: int, bit_width: int = 32):
        self.bits = bit_width
        self.value = decimal_value

    def _absolute_to_magnitude_bits(self, source_value: int, magnitude_width: int):
        magnitude_bits = [0] * magnitude_width
        absolute_value = abs(source_value)
        write_position = magnitude_width - 1

        while absolute_value > 0 and write_position >= 0:
            magnitude_bits[write_position] = absolute_value % 2
            absolute_value //= 2
            write_position -= 1

        return magnitude_bits

    def _add_binary_arrays(self, first_bits, second_bits):
        sum_bits = [0] * len(first_bits)
        carry_bit = 0

        for bit_position in range(len(first_bits) - 1, -1, -1):
            total_value = first_bits[bit_position] + second_bits[bit_position] + carry_bit
            sum_bits[bit_position] = total_value % 2
            carry_bit = total_value // 2

        return sum_bits, carry_bit

    def _unsigned_bits_to_decimal(self, bit_array):
        unsigned_value = 0
        for current_bit in bit_array:
            unsigned_value = unsigned_value * 2 + current_bit
        return unsigned_value

    def direct_code(self):
        if self.value == 0:
            return [0] * self.bits

        magnitude_bits = self._absolute_to_magnitude_bits(self.value, self.bits - 1)
        sign_bit = 1 if self.value < 0 else 0
        return [sign_bit] + magnitude_bits

    def inverse_code(self):
        direct_bits = self.direct_code()
        if self.value >= 0:
            return direct_bits

        inverted_magnitude = [1 - magnitude_bit for magnitude_bit in direct_bits[1:]]
        return [1] + inverted_magnitude

    def additional_code(self):
        inverse_bits = self.inverse_code()
        if self.value >= 0:
            return inverse_bits

        one_bits = [0] * self.bits
        one_bits[-1] = 1
        additional_bits, _ = self._add_binary_arrays(inverse_bits, one_bits)
        return additional_bits

    def add_additional(self, other_number):
        self_additional_bits = self.additional_code()
        other_additional_bits = other_number.additional_code()
        sum_bits, _ = self._add_binary_arrays(self_additional_bits, other_additional_bits)
        return sum_bits

    def negate_additional_bits(self, additional_bits):
        inverted_bits = [1 - source_bit for source_bit in additional_bits]
        one_bits = [0] * self.bits
        one_bits[-1] = 1
        negated_bits, _ = self._add_binary_arrays(inverted_bits, one_bits)
        return negated_bits

    def subtract(self, other_number):
        minuend_additional_bits = self.additional_code()
        subtrahend_additional_bits = other_number.additional_code()
        negated_subtrahend_bits = self.negate_additional_bits(subtrahend_additional_bits)
        difference_bits, _ = self._add_binary_arrays(minuend_additional_bits, negated_subtrahend_bits)
        return difference_bits

    def multiply_direct(self, other_number):
        result_sign_bit = 1 if (self.value < 0) ^ (other_number.value < 0) else 0

        left_magnitude_bits = self._absolute_to_magnitude_bits(self.value, self.bits - 1)
        right_magnitude_bits = self._absolute_to_magnitude_bits(other_number.value, self.bits - 1)

        product_magnitude_bits = [0] * (self.bits - 1)

        for right_bit_position in range(self.bits - 2, -1, -1):
            if right_magnitude_bits[right_bit_position] == 1:
                shift_distance = (self.bits - 2) - right_bit_position
                shifted_left_bits = left_magnitude_bits[:] + [0] * shift_distance
                shifted_left_bits = shifted_left_bits[-(self.bits - 1):]
                product_magnitude_bits, _ = self._add_binary_arrays(product_magnitude_bits, shifted_left_bits)

        return [result_sign_bit] + product_magnitude_bits

    def _unsigned_divmod(self, dividend_value: int, divisor_value: int):
        quotient_value = 0
        remainder_value = 0

        dividend_bits = []
        dividend_copy = dividend_value

        if dividend_copy == 0:
            dividend_bits = [0]
        else:
            while dividend_copy > 0:
                dividend_bits.insert(0, dividend_copy % 2)
                dividend_copy //= 2

        for current_bit in dividend_bits:
            remainder_value = remainder_value * 2 + current_bit
            quotient_value = quotient_value * 2
            if remainder_value >= divisor_value:
                remainder_value -= divisor_value
                quotient_value += 1

        return quotient_value, remainder_value

    def divide_direct(self, other_number, fractional_bit_count: int = 16):
        if other_number.value == 0:
            raise ZeroDivisionError("division by zero")

        result_sign_bit = 1 if (self.value < 0) ^ (other_number.value < 0) else 0
        absolute_dividend = abs(self.value)
        absolute_divisor = abs(other_number.value)

        integer_part_value, remainder_value = self._unsigned_divmod(absolute_dividend, absolute_divisor)

        fractional_part_value = 0
        for _ in range(fractional_bit_count):
            remainder_value *= 2
            fractional_part_value <<= 1
            if remainder_value >= absolute_divisor:
                fractional_part_value |= 1
                remainder_value -= absolute_divisor

        scaled_value = (integer_part_value << fractional_bit_count) | fractional_part_value
        scaled_magnitude_bits = self._absolute_to_magnitude_bits(scaled_value, self.bits - 1)
        return [result_sign_bit] + scaled_magnitude_bits

    def additional_to_decimal(self, additional_bits):
        if additional_bits[0] == 0:
            return self._unsigned_bits_to_decimal(additional_bits)

        absolute_bits = self.negate_additional_bits(additional_bits)
        return -self._unsigned_bits_to_decimal(absolute_bits)

    def direct_to_decimal(self, direct_bits):
        sign_multiplier = -1 if direct_bits[0] == 1 else 1
        magnitude_value = self._unsigned_bits_to_decimal(direct_bits[1:])
        return sign_multiplier * magnitude_value

    def direct_fixed_to_decimal(self, direct_bits, fractional_bit_count: int = 16):
        sign_multiplier = -1 if direct_bits[0] == 1 else 1

        scaled_value = self._unsigned_bits_to_decimal(direct_bits[1:])
        integer_part_value = scaled_value >> fractional_bit_count
        fractional_bits_value = scaled_value & ((1 << fractional_bit_count) - 1)

        decimal_value = integer_part_value
        fractional_weight = 0.5

        for bit_position in range(fractional_bit_count - 1, -1, -1):
            if (fractional_bits_value >> bit_position) & 1:
                decimal_value += fractional_weight
            fractional_weight /= 2

        return sign_multiplier * decimal_value

    def direct_fixed_to_decimal_string(self, direct_bits, precision: int = 5, fractional_bit_count: int = 16):
        sign_prefix = "-" if direct_bits[0] == 1 else ""

        scaled_value = self._unsigned_bits_to_decimal(direct_bits[1:])
        integer_part_value = scaled_value >> fractional_bit_count
        fractional_bits_value = scaled_value & ((1 << fractional_bit_count) - 1)

        decimal_digits = []
        for _ in range(precision):
            fractional_bits_value *= 10
            next_digit_value = fractional_bits_value >> fractional_bit_count
            decimal_digits.append(str(next_digit_value))
            fractional_bits_value &= (1 << fractional_bit_count) - 1

        return f"{sign_prefix}{integer_part_value}." + "".join(decimal_digits)
