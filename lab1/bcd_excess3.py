from constants import (
    BINARY_BASE,
    DECIMAL_BASE,
    EXCESS3_BIAS,
    EXCESS3_CARRY_DIGIT_BITS,
    EXCESS3_CARRY_THRESHOLD,
    EXCESS3_DIGIT_BIT_WIDTH,
    EXCESS3_MAX_DECIMAL_DIGIT,
    EXCESS3_PADDING_DIGIT_BITS,
    EXCESS3_ZERO_DIGIT,
)


class Excess3BCD:
    def int_to_bits(self, decimal_value, bit_width=EXCESS3_DIGIT_BIT_WIDTH):
        bit_array = [0] * bit_width
        write_position = bit_width - 1

        while decimal_value > 0 and write_position >= 0:
            bit_array[write_position] = decimal_value % BINARY_BASE
            decimal_value //= BINARY_BASE
            write_position -= 1

        return bit_array

    def bits_to_int(self, bit_array):
        decimal_value = 0
        for current_bit in bit_array:
            decimal_value = decimal_value * BINARY_BASE + current_bit
        return decimal_value

    def encode_digit(self, decimal_digit):
        excess3_value = decimal_digit + EXCESS3_BIAS
        return self.int_to_bits(excess3_value, EXCESS3_DIGIT_BIT_WIDTH)

    def decode_digit(self, encoded_digit_bits):
        encoded_value = self.bits_to_int(encoded_digit_bits)
        return encoded_value - EXCESS3_BIAS

    def encode_number(self, decimal_number):
        if decimal_number < 0:
            raise ValueError("Excess-3 in this implementation supports only non-negative numbers")

        decimal_digits = []
        if decimal_number == 0:
            decimal_digits = [EXCESS3_ZERO_DIGIT]
        else:
            while decimal_number > 0:
                decimal_digits.append(decimal_number % DECIMAL_BASE)
                decimal_number //= DECIMAL_BASE
            decimal_digits.reverse()

        encoded_number_bits = []
        for current_digit in decimal_digits:
            encoded_number_bits.extend(self.encode_digit(current_digit))

        return encoded_number_bits

    def decode_number(self, encoded_number_bits):
        if len(encoded_number_bits) % EXCESS3_DIGIT_BIT_WIDTH != 0:
            raise ValueError("Invalid Excess-3 bit length")

        decoded_number = 0
        for block_start in range(0, len(encoded_number_bits), EXCESS3_DIGIT_BIT_WIDTH):
            encoded_digit_bits = encoded_number_bits[block_start:block_start + EXCESS3_DIGIT_BIT_WIDTH]
            decoded_digit = self.decode_digit(encoded_digit_bits)
            if decoded_digit < EXCESS3_ZERO_DIGIT or decoded_digit > EXCESS3_MAX_DECIMAL_DIGIT:
                raise ValueError("Invalid Excess-3 digit")
            decoded_number = decoded_number * DECIMAL_BASE + decoded_digit

        return decoded_number

    def add(self, left_number, right_number):
        left_encoded_bits = self.encode_number(left_number)
        right_encoded_bits = self.encode_number(right_number)

        digit_count = max(len(left_encoded_bits), len(right_encoded_bits)) // EXCESS3_DIGIT_BIT_WIDTH

        while len(left_encoded_bits) < digit_count * EXCESS3_DIGIT_BIT_WIDTH:
            left_encoded_bits = EXCESS3_PADDING_DIGIT_BITS + left_encoded_bits

        while len(right_encoded_bits) < digit_count * EXCESS3_DIGIT_BIT_WIDTH:
            right_encoded_bits = EXCESS3_PADDING_DIGIT_BITS + right_encoded_bits

        result_encoded_bits = [0] * (digit_count * EXCESS3_DIGIT_BIT_WIDTH)
        carry_value = 0

        for digit_index in range(digit_count - 1, -1, -1):
            block_start = digit_index * EXCESS3_DIGIT_BIT_WIDTH

            left_digit_code = self.bits_to_int(left_encoded_bits[block_start:block_start + EXCESS3_DIGIT_BIT_WIDTH])
            right_digit_code = self.bits_to_int(right_encoded_bits[block_start:block_start + EXCESS3_DIGIT_BIT_WIDTH])
            digit_sum_code = left_digit_code + right_digit_code + carry_value

            if digit_sum_code >= EXCESS3_CARRY_THRESHOLD:
                carry_value = 1
                digit_sum_code = digit_sum_code - EXCESS3_CARRY_THRESHOLD + EXCESS3_BIAS
            else:
                carry_value = 0
                digit_sum_code = digit_sum_code - EXCESS3_BIAS

            result_encoded_bits[block_start:block_start + EXCESS3_DIGIT_BIT_WIDTH] = self.int_to_bits(
                digit_sum_code,
                EXCESS3_DIGIT_BIT_WIDTH,
            )

        if carry_value == 1:
            result_encoded_bits = EXCESS3_CARRY_DIGIT_BITS + result_encoded_bits

        return result_encoded_bits
