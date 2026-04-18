from binary_int import BinaryInt
from float_ieee754 import Float32
from bcd_excess3 import Excess3BCD
from constants import CLI_SEPARATOR_WIDTH, DEFAULT_DECIMAL_PRECISION, DEFAULT_FRACTIONAL_BIT_COUNT


def bit_array_to_string(bit_array):
    return "".join(str(current_bit) for current_bit in bit_array)


def direct_fixed_bits_to_string(direct_bits, fractional_bit_count=DEFAULT_FRACTIONAL_BIT_COUNT):
    sign_bit_text = str(direct_bits[0])
    magnitude_bits = direct_bits[1:]
    integer_bits = magnitude_bits[:len(magnitude_bits) - fractional_bit_count]
    fractional_bits = magnitude_bits[len(magnitude_bits) - fractional_bit_count:]
    return sign_bit_text + " " + "".join(str(bit_value) for bit_value in integer_bits) + "." + "".join(
        str(bit_value) for bit_value in fractional_bits
    )


def print_separator():
    print("=" * CLI_SEPARATOR_WIDTH)


def read_int(prompt_text, allow_negative=True):
    while True:
        raw_text = input(prompt_text).strip()
        try:
            parsed_value = int(raw_text)
            if not allow_negative and parsed_value < 0:
                print("Введите неотрицательное целое число.")
                continue
            return parsed_value
        except ValueError:
            print("Некорректный ввод. Нужно целое число.")


def read_float(prompt_text):
    while True:
        raw_text = input(prompt_text).strip()
        try:
            return float(raw_text)
        except ValueError:
            print("Некорректный ввод. Нужно число с плавающей точкой.")


def menu_print():
    print_separator()
    print("AOIS LAB CLI")
    print_separator()
    print("1. Показать прямой/обратный/дополнительный код числа")
    print("2. Сложение 2 чисел в дополнительном коде")
    print("3. Вычитание через отрицание и сложение в дополнительном коде")
    print("4. Умножение 2 чисел в прямом коде")
    print("5. Деление 2 чисел в прямом коде (точность 5 знаков)")
    print("6. IEEE-754 (32 бита): +, -, *, /")
    print("7. Excess-3: сложение 2 чисел")
    print("0. Выход")


def run_integer_codes():
    print_separator()
    print("КОДЫ ЦЕЛОГО ЧИСЛА")
    print_separator()
    decimal_number = read_int("Введите целое число: ")
    integer_number = BinaryInt(decimal_number)
    print("Decimal    :", integer_number.value)
    print("Direct     :", bit_array_to_string(integer_number.direct_code()))
    print("Inverse    :", bit_array_to_string(integer_number.inverse_code()))
    print("Additional :", bit_array_to_string(integer_number.additional_code()))


def run_additional_addition():
    print_separator()
    print("СЛОЖЕНИЕ В ДОПОЛНИТЕЛЬНОМ КОДЕ")
    print_separator()
    left_number = BinaryInt(read_int("Введите первое число: "))
    right_number = BinaryInt(read_int("Введите второе число: "))
    result_bits = left_number.add_additional(right_number)
    result_decimal = left_number.additional_to_decimal(result_bits)
    print("Expression :", left_number.value, "+", right_number.value)
    print("Binary     :", bit_array_to_string(result_bits))
    print("Decimal    :", result_decimal)


def run_additional_subtraction():
    print_separator()
    print("ВЫЧИТАНИЕ ЧЕРЕЗ ОТРИЦАНИЕ + СЛОЖЕНИЕ")
    print_separator()
    left_number = BinaryInt(read_int("Введите уменьшаемое: "))
    right_number = BinaryInt(read_int("Введите вычитаемое: "))
    result_bits = left_number.subtract(right_number)
    result_decimal = left_number.additional_to_decimal(result_bits)
    print("Expression :", left_number.value, "-", right_number.value)
    print("Binary     :", bit_array_to_string(result_bits))
    print("Decimal    :", result_decimal)


def run_direct_multiplication():
    print_separator()
    print("УМНОЖЕНИЕ В ПРЯМОМ КОДЕ")
    print_separator()
    left_number = BinaryInt(read_int("Введите первый множитель: "))
    right_number = BinaryInt(read_int("Введите второй множитель: "))
    result_bits = left_number.multiply_direct(right_number)
    result_decimal = left_number.direct_to_decimal(result_bits)
    print("Expression :", left_number.value, "*", right_number.value)
    print("Binary     :", bit_array_to_string(result_bits))
    print("Decimal    :", result_decimal)


def run_direct_division():
    print_separator()
    print("ДЕЛЕНИЕ В ПРЯМОМ КОДЕ")
    print_separator()
    left_number = BinaryInt(read_int("Введите делимое: "))
    right_number = BinaryInt(read_int("Введите делитель: "))
    try:
        result_bits = left_number.divide_direct(right_number, fractional_bit_count=DEFAULT_FRACTIONAL_BIT_COUNT)
    except ZeroDivisionError:
        print("Ошибка: деление на ноль.")
        return

    result_decimal = left_number.direct_fixed_to_decimal_string(
        result_bits,
        precision=DEFAULT_DECIMAL_PRECISION,
        fractional_bit_count=DEFAULT_FRACTIONAL_BIT_COUNT,
    )
    print("Expression :", left_number.value, "/", right_number.value)
    print("Binary     :", bit_array_to_string(result_bits))
    print("Binary fmt :", direct_fixed_bits_to_string(result_bits, fractional_bit_count=DEFAULT_FRACTIONAL_BIT_COUNT))
    print("Decimal    :", result_decimal)


def run_ieee754_operations():
    print_separator()
    print("IEEE-754 (32 БИТА): +, -, *, /")
    print_separator()
    left_number = Float32(read_float("Введите первое число: "))
    right_number = Float32(read_float("Введите второе число: "))

    left_bits = left_number.to_ieee754()
    right_bits = right_number.to_ieee754()

    print("A (dec)    :", left_number.value)
    print("A (bits)   :", bit_array_to_string(left_bits))
    print("A (check)  :", left_number.ieee_bits_to_decimal(left_bits))
    print()
    print("B (dec)    :", right_number.value)
    print("B (bits)   :", bit_array_to_string(right_bits))
    print("B (check)  :", right_number.ieee_bits_to_decimal(right_bits))

    add_bits = left_number.add(right_number)
    sub_bits = left_number.subtract(right_number)
    mul_bits = left_number.multiply(right_number)

    print()
    print("A + B bits :", bit_array_to_string(add_bits))
    print("A + B dec  :", left_number.ieee_bits_to_decimal(add_bits))
    print("A - B bits :", bit_array_to_string(sub_bits))
    print("A - B dec  :", left_number.ieee_bits_to_decimal(sub_bits))
    print("A * B bits :", bit_array_to_string(mul_bits))
    print("A * B dec  :", left_number.ieee_bits_to_decimal(mul_bits))

    try:
        div_bits = left_number.divide(right_number)
        print("A / B bits :", bit_array_to_string(div_bits))
        print("A / B dec  :", left_number.ieee_bits_to_decimal(div_bits))
    except ZeroDivisionError:
        print("A / B      : ошибка деления на ноль")


def run_excess3_addition():
    print_separator()
    print("EXCESS-3: СЛОЖЕНИЕ")
    print_separator()
    codec = Excess3BCD()
    left_number = read_int("Введите первое неотрицательное число: ", allow_negative=False)
    right_number = read_int("Введите второе неотрицательное число: ", allow_negative=False)

    left_bits = codec.encode_number(left_number)
    right_bits = codec.encode_number(right_number)
    sum_bits = codec.add(left_number, right_number)

    print("A (dec)    :", left_number)
    print("A (bits)   :", bit_array_to_string(left_bits))
    print("A (check)  :", codec.decode_number(left_bits))
    print()
    print("B (dec)    :", right_number)
    print("B (bits)   :", bit_array_to_string(right_bits))
    print("B (check)  :", codec.decode_number(right_bits))
    print()
    print("A + B bits :", bit_array_to_string(sum_bits))
    print("A + B dec  :", codec.decode_number(sum_bits))


def main():
    action_map = {
        "1": run_integer_codes,
        "2": run_additional_addition,
        "3": run_additional_subtraction,
        "4": run_direct_multiplication,
        "5": run_direct_division,
        "6": run_ieee754_operations,
        "7": run_excess3_addition,
    }

    while True:
        menu_print()
        selected_action = input("Выберите пункт меню: ").strip()

        if selected_action == "0":
            print("Выход из программы.")
            break

        action = action_map.get(selected_action)
        if action is None:
            print("Неверный пункт меню. Повторите ввод.")
            continue

        action()
        print()
        input("Нажмите Enter, чтобы вернуться в меню...")


if __name__ == "__main__":
    main()
