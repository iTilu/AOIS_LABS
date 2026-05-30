from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from minimizer import minimize_sdnf


BitTuple = tuple[int, ...]


@dataclass(frozen=True)
class OutputFunctionReport:
    name: str
    minterms: tuple[BitTuple, ...]
    dont_cares: tuple[BitTuple, ...]
    minimized_expression: str


@dataclass(frozen=True)
class SectionReport:
    table_lines: tuple[str, ...]
    outputs: tuple[OutputFunctionReport, ...]
    example_lines: tuple[str, ...]


def _format_table(rows: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]

    def build_row(row: tuple[str, ...]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)
    return tuple([build_row(rows[0]), separator, *[build_row(row) for row in rows[1:]]])


def _bits_to_text(bits: tuple[int, ...]) -> str:
    return "".join(str(bit) for bit in bits)


def _int_to_bits(value: int, width: int) -> BitTuple:
    return tuple((value >> shift) & 1 for shift in range(width - 1, -1, -1))


def _build_5421_table() -> dict[int, BitTuple]:
    return {
        0: (0, 0, 0, 0),
        1: (0, 0, 0, 1),
        2: (0, 0, 1, 0),
        3: (0, 0, 1, 1),
        4: (0, 1, 0, 0),
        5: (1, 0, 0, 0),
        6: (1, 0, 0, 1),
        7: (1, 0, 1, 0),
        8: (1, 0, 1, 1),
        9: (1, 1, 0, 0),
    }


CODE_5421 = _build_5421_table()


def build_binary_adder_report() -> SectionReport:
    variable_names = ("A", "B", "Cin")
    truth_rows = [("A", "B", "Cin", "S", "Cout")]
    sum_minterms: list[BitTuple] = []
    carry_minterms: list[BitTuple] = []

    for bits in product((0, 1), repeat=3):
        total = sum(bits)
        sum_bit = total % 2
        carry_bit = total // 2
        if sum_bit == 1:
            sum_minterms.append(bits)
        if carry_bit == 1:
            carry_minterms.append(bits)
        truth_rows.append((*map(str, bits), str(sum_bit), str(carry_bit)))

    outputs = (
        OutputFunctionReport(
            name="S",
            minterms=tuple(sum_minterms),
            dont_cares=tuple(),
            minimized_expression=minimize_sdnf(variable_names, tuple(sum_minterms)).expression,
        ),
        OutputFunctionReport(
            name="Cout",
            minterms=tuple(carry_minterms),
            dont_cares=tuple(),
            minimized_expression=minimize_sdnf(variable_names, tuple(carry_minterms)).expression,
        ),
    )

    example_lines = (
        "Example 8-bit ripple-carry addition:",
        "  00001000 (8)",
        "+ 00000110 (6)",
        "= 00001110 (14)",
    )
    return SectionReport(_format_table(tuple(truth_rows)), outputs, example_lines)


def build_5421_adder_report() -> SectionReport:
    variable_names = ("X3", "X2", "X1", "X0", "Y3", "Y2", "Y1", "Y0")
    valid_inputs = set()
    carry_minterms: list[BitTuple] = []
    result_bit_minterms: list[list[BitTuple]] = [[], [], [], []]
    preview_rows = [("x", "X-code", "y", "Y-code", "sum", "carry", "Z-code")]

    for left_digit, left_code in CODE_5421.items():
        for right_digit, right_code in CODE_5421.items():
            assignment = (*left_code, *right_code)
            valid_inputs.add(assignment)

            total = left_digit + right_digit
            carry = 1 if total >= 10 else 0
            units_digit = total % 10
            units_code = CODE_5421[units_digit]

            if carry == 1:
                carry_minterms.append(assignment)

            for bit_index, bit_value in enumerate(units_code):
                if bit_value == 1:
                    result_bit_minterms[bit_index].append(assignment)

            if len(preview_rows) < 21:
                preview_rows.append(
                    (
                        str(left_digit),
                        _bits_to_text(left_code),
                        str(right_digit),
                        _bits_to_text(right_code),
                        str(total),
                        str(carry),
                        _bits_to_text(units_code),
                    )
                )

    dont_cares = tuple(sorted(set(product((0, 1), repeat=8)) - valid_inputs))
    outputs = [
        OutputFunctionReport(
            name="Carry10",
            minterms=tuple(carry_minterms),
            dont_cares=dont_cares,
            minimized_expression=minimize_sdnf(variable_names, tuple(carry_minterms), dont_cares).expression,
        )
    ]
    for bit_index, minterms in enumerate(result_bit_minterms):
        outputs.append(
            OutputFunctionReport(
                name=f"Z{3 - bit_index}",
                minterms=tuple(minterms),
                dont_cares=dont_cares,
                minimized_expression=minimize_sdnf(variable_names, tuple(minterms), dont_cares).expression,
            )
        )

    example_lines = (
        "Example for variant C + d (5421 BCD with correction-digit carry):",
        f"  8 -> {_bits_to_text(CODE_5421[8])}",
        f"  6 -> {_bits_to_text(CODE_5421[6])}",
        "  8 + 6 = 14",
        "  Carry10 = 1",
        f"  Units tetrad (4) -> {_bits_to_text(CODE_5421[4])}",
        "  Full decimal result is reconstructed as 1|0100 -> 14.",
    )
    return SectionReport(_format_table(tuple(preview_rows)), tuple(outputs), example_lines)


def build_down_counter_report() -> SectionReport:
    variable_names = ("Q2", "Q1", "Q0")
    rows = [("Q2", "Q1", "Q0", "Q2'", "Q1'", "Q0'", "T2", "T1", "T0")]
    t2_minterms: list[BitTuple] = []
    t1_minterms: list[BitTuple] = []
    t0_minterms: list[BitTuple] = []

    for state in range(7, -1, -1):
        current_bits = _int_to_bits(state, 3)
        next_bits = _int_to_bits((state - 1) % 8, 3)
        t_bits = tuple(current ^ next_bit for current, next_bit in zip(current_bits, next_bits))

        if t_bits[0] == 1:
            t2_minterms.append(current_bits)
        if t_bits[1] == 1:
            t1_minterms.append(current_bits)
        if t_bits[2] == 1:
            t0_minterms.append(current_bits)

        rows.append((*map(str, current_bits), *map(str, next_bits), *map(str, t_bits)))

    outputs = (
        OutputFunctionReport(
            name="T2",
            minterms=tuple(t2_minterms),
            dont_cares=tuple(),
            minimized_expression=minimize_sdnf(variable_names, tuple(t2_minterms)).expression,
        ),
        OutputFunctionReport(
            name="T1",
            minterms=tuple(t1_minterms),
            dont_cares=tuple(),
            minimized_expression=minimize_sdnf(variable_names, tuple(t1_minterms)).expression,
        ),
        OutputFunctionReport(
            name="T0",
            minterms=tuple(t0_minterms),
            dont_cares=tuple(),
            minimized_expression=minimize_sdnf(variable_names, tuple(t0_minterms)).expression,
        ),
    )

    example_lines = (
        "Countdown cycle:",
        "  111 -> 110 -> 101 -> 100 -> 011 -> 010 -> 001 -> 000 -> 111",
        "Meaning of T flip-flop excitation:",
        "  T = 0 keeps the bit unchanged.",
        "  T = 1 toggles the bit on the next clock.",
    )
    return SectionReport(_format_table(tuple(rows)), outputs, example_lines)


def build_variant_report() -> str:
    adder_report = build_binary_adder_report()
    weighted_code_report = build_5421_adder_report()
    counter_report = build_down_counter_report()

    code_rows = [("Digit", "5421-code")]
    for digit, code in CODE_5421.items():
        code_rows.append((str(digit), _bits_to_text(code)))

    lines: list[str] = [
        "LAB 3 VARIANT REPORT",
        "Variant mapping: part 1 -> 1, part 2 -> C + d, part 3 -> 2",
        "",
        "PART 1. One-bit full adder with 3 inputs (SDNF)",
        "Truth table:",
        *adder_report.table_lines,
        "",
    ]
    for output in adder_report.outputs:
        lines.append(f"{output.name}:")
        lines.append(f"  minterms: {', '.join(_bits_to_text(bits) for bits in output.minterms)}")
        lines.append(f"  minimized SDNF: {output.minimized_expression}")

    lines.extend(["", *adder_report.example_lines, "", "PART 2. Decimal adder in 5421 BCD, variant C with n=6", "Code table:"])
    lines.extend(_format_table(tuple(code_rows)))
    lines.extend(["", "Preview of valid truth-table rows:"])
    lines.extend(weighted_code_report.table_lines)
    lines.append("")
    for output in weighted_code_report.outputs:
        lines.append(f"{output.name}:")
        lines.append(f"  minterm count: {len(output.minterms)}")
        lines.append(f"  dont-care count: {len(output.dont_cares)}")
        lines.append(f"  minimized SDNF: {output.minimized_expression}")

    lines.extend(["", *weighted_code_report.example_lines, "", "PART 3. Binary down counter on 8 states with T flip-flops", "State table:"])
    lines.extend(counter_report.table_lines)
    lines.append("")
    for output in counter_report.outputs:
        lines.append(f"{output.name}:")
        lines.append(f"  minterms: {', '.join(_bits_to_text(bits) for bits in output.minterms)}")
        lines.append(f"  minimized SDNF: {output.minimized_expression}")
    lines.extend(["", *counter_report.example_lines])
    return "\n".join(lines)
