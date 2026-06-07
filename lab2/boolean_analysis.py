from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

from logic_parser import ExpressionNode, parse_expression


BitPattern = tuple[int | None, ...]


@dataclass(frozen=True)
class TruthTableRow:
    variable_values: tuple[int, ...]
    subexpression_values: tuple[int, ...]
    result_value: int


@dataclass(frozen=True)
class MinimizationResult:
    minimized_expression: str
    prime_implicants: tuple[BitPattern, ...]
    selected_implicants: tuple[BitPattern, ...]
    gluing_stages: tuple[tuple[BitPattern, ...], ...]
    coverage_table_lines: tuple[str, ...]


def _format_table(table_rows: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    if not table_rows:
        return tuple()

    column_count = len(table_rows[0])
    column_widths = [
        max(len(row[column_index]) for row in table_rows)
        for column_index in range(column_count)
    ]

    def build_row(row: tuple[str, ...]) -> str:
        return " | ".join(
            cell_value.ljust(column_widths[column_index])
            for column_index, cell_value in enumerate(row)
        )

    separator_line = " | ".join("_" * column_width for column_width in column_widths)
    formatted_lines = [build_row(table_rows[0]), separator_line]
    formatted_lines.extend(build_row(row) for row in table_rows[1:])
    return tuple(formatted_lines)


def _iterate_bit_vectors(variable_count: int):
    return product((0, 1), repeat=variable_count)


def _count_defined_bits(bit_pattern: BitPattern) -> int:
    return sum(bit_value is not None for bit_value in bit_pattern)


def _combine_patterns(first_pattern: BitPattern, second_pattern: BitPattern) -> BitPattern | None:
    mismatch_count = 0
    combined_values: list[int | None] = []

    for first_bit, second_bit in zip(first_pattern, second_pattern):
        if first_bit == second_bit:
            combined_values.append(first_bit)
            continue
        if first_bit is None or second_bit is None:
            return None
        mismatch_count += 1
        combined_values.append(None)
        if mismatch_count > 1:
            return None

    if mismatch_count != 1:
        return None
    return tuple(combined_values)


def _pattern_covers_value(bit_pattern: BitPattern, bit_values: tuple[int, ...]) -> bool:
    for expected_bit, actual_bit in zip(bit_pattern, bit_values):
        if expected_bit is not None and expected_bit != actual_bit:
            return False
    return True


def _pattern_sort_key(bit_pattern: BitPattern) -> tuple[int, tuple[int, ...]]:
    normalized_values = tuple(-1 if bit_value is None else bit_value for bit_value in bit_pattern)
    return (_count_defined_bits(bit_pattern), normalized_values)


def _format_dnf_term(bit_pattern: BitPattern, variable_names: tuple[str, ...]) -> str:
    if all(bit_value is None for bit_value in bit_pattern):
        return "1"
    fragments: list[str] = []
    for variable_name, bit_value in zip(variable_names, bit_pattern):
        if bit_value is None:
            continue
        fragments.append(variable_name if bit_value == 1 else f"!{variable_name}")
    return "&".join(fragments)


def _format_cnf_clause(bit_pattern: BitPattern, variable_names: tuple[str, ...]) -> str:
    if all(bit_value is None for bit_value in bit_pattern):
        return "0"
    fragments: list[str] = []
    for variable_name, bit_value in zip(variable_names, bit_pattern):
        if bit_value is None:
            continue
        fragments.append(variable_name if bit_value == 0 else f"!{variable_name}")
    return "(" + "|".join(fragments) + ")"


def _format_pattern_for_stage(bit_pattern: BitPattern, variable_names: tuple[str, ...], form: str) -> str:
    if form == "dnf":
        return _format_dnf_term(bit_pattern, variable_names)
    return _format_cnf_clause(bit_pattern, variable_names)


def _all_assignments_covered(patterns: tuple[BitPattern, ...], required_assignments: tuple[tuple[int, ...], ...]) -> bool:
    return all(any(_pattern_covers_value(pattern, assignment) for pattern in patterns) for assignment in required_assignments)


def _select_cover(prime_implicants: tuple[BitPattern, ...], required_assignments: tuple[tuple[int, ...], ...]) -> tuple[BitPattern, ...]:
    if not required_assignments:
        return tuple()

    essential_indices: set[int] = set()
    uncovered_assignments = set(required_assignments)

    for assignment in required_assignments:
        covering_indices = [
            pattern_index
            for pattern_index, bit_pattern in enumerate(prime_implicants)
            if _pattern_covers_value(bit_pattern, assignment)
        ]
        if len(covering_indices) == 1:
            essential_indices.add(covering_indices[0])

    for essential_index in essential_indices:
        bit_pattern = prime_implicants[essential_index]
        uncovered_assignments = {
            assignment for assignment in uncovered_assignments if not _pattern_covers_value(bit_pattern, assignment)
        }

    if not uncovered_assignments:
        return tuple(sorted((prime_implicants[index] for index in essential_indices), key=_pattern_sort_key))

    remaining_indices = [index for index in range(len(prime_implicants)) if index not in essential_indices]
    best_choice: tuple[int, ...] | None = None

    for subset_size in range(1, len(remaining_indices) + 1):
        for subset in combinations(remaining_indices, subset_size):
            chosen_patterns = tuple(prime_implicants[index] for index in sorted((*essential_indices, *subset)))
            if not _all_assignments_covered(chosen_patterns, tuple(uncovered_assignments)):
                continue

            current_weight = sum(_count_defined_bits(bit_pattern) for bit_pattern in chosen_patterns)
            if best_choice is None:
                best_choice = subset
                continue

            previous_patterns = tuple(prime_implicants[index] for index in sorted((*essential_indices, *best_choice)))
            previous_weight = sum(_count_defined_bits(bit_pattern) for bit_pattern in previous_patterns)
            chosen_signature = tuple(_pattern_sort_key(bit_pattern) for bit_pattern in chosen_patterns)
            previous_signature = tuple(_pattern_sort_key(bit_pattern) for bit_pattern in previous_patterns)
            if (len(chosen_patterns), current_weight, chosen_signature) < (
                len(previous_patterns),
                previous_weight,
                previous_signature,
            ):
                best_choice = subset
        if best_choice is not None:
            break

    selected_indices = sorted((*essential_indices, *(best_choice or tuple())))
    return tuple(sorted((prime_implicants[index] for index in selected_indices), key=_pattern_sort_key))


def _petrick_cover(
    prime_implicants: tuple[BitPattern, ...],
    required_assignments: tuple[tuple[int, ...], ...],
    excluded_indices: set[int],
) -> tuple[int, ...]:
    available_indices = [index for index in range(len(prime_implicants)) if index not in excluded_indices]
    cover_options: list[tuple[int, ...]] = []
    for assignment in required_assignments:
        covering_indices = tuple(
            index
            for index in available_indices
            if _pattern_covers_value(prime_implicants[index], assignment)
        )
        if not covering_indices:
            return tuple()
        cover_options.append(covering_indices)

    solutions: list[tuple[int, ...]] = [tuple()]
    for cover_option in cover_options:
        next_solutions: list[tuple[int, ...]] = []
        for current_solution in solutions:
            for prime_index in cover_option:
                next_solutions.append(tuple(sorted(set((*current_solution, prime_index)))))
        solutions = next_solutions

    best_solution: tuple[int, ...] | None = None
    best_signature: tuple[int, int, tuple[tuple[int, tuple[int, ...]], ...]] | None = None
    for solution in solutions:
        chosen_patterns = tuple(prime_implicants[index] for index in solution)
        signature = (
            len(solution),
            sum(_count_defined_bits(bit_pattern) for bit_pattern in chosen_patterns),
            tuple(_pattern_sort_key(bit_pattern) for bit_pattern in chosen_patterns),
        )
        if best_signature is None or signature < best_signature:
            best_signature = signature
            best_solution = solution
    return best_solution or tuple()


def _select_cover_table(
    prime_implicants: tuple[BitPattern, ...],
    required_assignments: tuple[tuple[int, ...], ...],
) -> tuple[BitPattern, ...]:
    if not required_assignments:
        return tuple()

    selected_indices: set[int] = set()
    uncovered_assignments = list(required_assignments)

    while uncovered_assignments:
        essential_indices: set[int] = set()
        for assignment in uncovered_assignments:
            covering_indices = [
                pattern_index
                for pattern_index, bit_pattern in enumerate(prime_implicants)
                if pattern_index not in selected_indices and _pattern_covers_value(bit_pattern, assignment)
            ]
            if len(covering_indices) == 1:
                essential_indices.add(covering_indices[0])

        if essential_indices:
            selected_indices.update(essential_indices)
            uncovered_assignments = [
                assignment
                for assignment in uncovered_assignments
                if not any(_pattern_covers_value(prime_implicants[index], assignment) for index in selected_indices)
            ]
            continue

        petrick_indices = _petrick_cover(prime_implicants, tuple(uncovered_assignments), selected_indices)
        selected_indices.update(petrick_indices)
        uncovered_assignments = [
            assignment
            for assignment in uncovered_assignments
            if not any(_pattern_covers_value(prime_implicants[index], assignment) for index in selected_indices)
        ]

    return tuple(sorted((prime_implicants[index] for index in selected_indices), key=_pattern_sort_key))


def _assignment_to_map_cell(
    assignment: tuple[int, ...],
    row_count: int,
    row_codes: tuple[str, ...],
    col_codes: tuple[str, ...],
) -> tuple[int, int]:
    row_bits = "".join(str(assignment[variable_index]) for variable_index in range(row_count))
    column_bits = "".join(str(assignment[variable_index]) for variable_index in range(row_count, len(assignment)))
    row_index = row_codes.index(row_bits) if row_count else 0
    column_index = col_codes.index(column_bits) if column_bits else 0
    return row_index, column_index


def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def _rectangle_cells(
    start_row: int,
    start_column: int,
    height: int,
    width: int,
    row_grid_size: int,
    column_grid_size: int,
) -> frozenset[tuple[int, int]]:
    return frozenset(
        ((start_row + row_offset) % row_grid_size, (start_column + column_offset) % column_grid_size)
        for row_offset in range(height)
        for column_offset in range(width)
    )


def _is_valid_karnaugh_group(
    cells: frozenset[tuple[int, int]],
    row_grid_size: int,
    column_grid_size: int,
) -> bool:
    cell_count = len(cells)
    if cell_count == 0 or not _is_power_of_two(cell_count):
        return False
    if cell_count == 1:
        return True

    height_power = 0
    while (1 << height_power) <= cell_count:
        height = 1 << height_power
        if cell_count % height != 0:
            height_power += 1
            continue
        width = cell_count // height
        if not _is_power_of_two(width):
            height_power += 1
            continue
        for start_row in range(row_grid_size):
            for start_column in range(column_grid_size):
                if _rectangle_cells(start_row, start_column, height, width, row_grid_size, column_grid_size) == cells:
                    return True
        height_power += 1
    return False


def _groups_can_merge_on_map(
    first_group: tuple[BitPattern, frozenset[tuple[int, int]]],
    second_group: tuple[BitPattern, frozenset[tuple[int, int]]],
    row_grid_size: int,
    column_grid_size: int,
) -> BitPattern | None:
    first_pattern, first_cells = first_group
    second_pattern, second_cells = second_group
    combined_pattern = _combine_patterns(first_pattern, second_pattern)
    if combined_pattern is None or len(first_cells) != len(second_cells):
        return None

    merged_cells = first_cells | second_cells
    if not _is_valid_karnaugh_group(merged_cells, row_grid_size, column_grid_size):
        return None
    return combined_pattern


def _build_karnaugh_prime_implicants(
    initial_patterns: tuple[BitPattern, ...],
    variable_names: tuple[str, ...],
) -> tuple[tuple[BitPattern, ...], tuple[BitPattern, ...]]:
    variable_count = len(variable_names)
    row_variable_count = variable_count // 2
    column_variable_count = variable_count - row_variable_count
    row_codes = _gray_code(row_variable_count)
    column_codes = _gray_code(column_variable_count)
    row_grid_size = len(row_codes)
    column_grid_size = len(column_codes)

    current_groups = tuple(
        sorted(
            (
                (
                    bit_pattern,
                    frozenset({_assignment_to_map_cell(bit_pattern, row_variable_count, row_codes, column_codes)}),
                )
                for bit_pattern in set(initial_patterns)
            ),
            key=lambda group: _pattern_sort_key(group[0]),
        )
    )
    gluing_stages: list[tuple[BitPattern, ...]] = [tuple(group[0] for group in current_groups)]
    prime_implicants: set[BitPattern] = set()

    while current_groups:
        used_groups: set[tuple[BitPattern, frozenset[tuple[int, int]]]] = set()
        next_groups: dict[BitPattern, frozenset[tuple[int, int]]] = {}
        for first_index, first_group in enumerate(current_groups):
            for second_group in current_groups[first_index + 1 :]:
                combined_pattern = _groups_can_merge_on_map(
                    first_group,
                    second_group,
                    row_grid_size,
                    column_grid_size,
                )
                if combined_pattern is None:
                    continue
                used_groups.add(first_group)
                used_groups.add(second_group)
                merged_cells = first_group[1] | second_group[1]
                if combined_pattern in next_groups:
                    next_groups[combined_pattern] |= merged_cells
                else:
                    next_groups[combined_pattern] = merged_cells

        for group in current_groups:
            if group not in used_groups:
                prime_implicants.add(group[0])

        if not next_groups:
            break
        current_groups = tuple(
            sorted(
                ((bit_pattern, next_groups[bit_pattern]) for bit_pattern in next_groups),
                key=lambda group: _pattern_sort_key(group[0]),
            )
        )
        gluing_stages.append(tuple(group[0] for group in current_groups))

    return tuple(gluing_stages), tuple(sorted(prime_implicants, key=_pattern_sort_key))


def _build_prime_implicants(initial_patterns: tuple[BitPattern, ...]) -> tuple[tuple[BitPattern, ...], tuple[BitPattern, ...]]:
    current_patterns = tuple(sorted(set(initial_patterns), key=_pattern_sort_key))
    gluing_stages: list[tuple[BitPattern, ...]] = [current_patterns]
    prime_implicants: set[BitPattern] = set()

    while current_patterns:
        used_patterns: set[BitPattern] = set()
        next_patterns: set[BitPattern] = set()
        for first_index, first_pattern in enumerate(current_patterns):
            for second_pattern in current_patterns[first_index + 1 :]:
                combined_pattern = _combine_patterns(first_pattern, second_pattern)
                if combined_pattern is None:
                    continue
                used_patterns.add(first_pattern)
                used_patterns.add(second_pattern)
                next_patterns.add(combined_pattern)

        for bit_pattern in current_patterns:
            if bit_pattern not in used_patterns:
                prime_implicants.add(bit_pattern)

        if not next_patterns:
            break
        current_patterns = tuple(sorted(next_patterns, key=_pattern_sort_key))
        gluing_stages.append(current_patterns)

    return tuple(gluing_stages), tuple(sorted(prime_implicants, key=_pattern_sort_key))


def _build_coverage_table_lines(
    implicants: tuple[BitPattern, ...],
    required_assignments: tuple[tuple[int, ...], ...],
    variable_names: tuple[str, ...],
    form: str,
    selected_implicants: tuple[BitPattern, ...] | None = None,
) -> tuple[str, ...]:
    if not implicants:
        return tuple()

    table_rows: list[tuple[str, ...]] = [
        tuple(["Импликанта", *["".join(str(bit_value) for bit_value in assignment) for assignment in required_assignments]])
    ]
    selected_set = set(selected_implicants or implicants)
    for bit_pattern in implicants:
        marker_cells = ["X" if _pattern_covers_value(bit_pattern, assignment) else "." for assignment in required_assignments]
        label = _format_pattern_for_stage(bit_pattern, variable_names, form)
        if selected_implicants is not None and bit_pattern in selected_set:
            label = f"*{label}"
        table_rows.append(tuple([label, *marker_cells]))
    return _format_table(tuple(table_rows))


def _format_minimized_expression(
    selected_implicants: tuple[BitPattern, ...],
    variable_names: tuple[str, ...],
    form: str,
) -> str:
    if form == "dnf":
        formatted_terms = sorted(_format_dnf_term(bit_pattern, variable_names) for bit_pattern in selected_implicants)
        return " | ".join(formatted_terms)
    formatted_clauses = sorted(_format_cnf_clause(bit_pattern, variable_names) for bit_pattern in selected_implicants)
    return " & ".join(formatted_clauses)


def _minimize_constant_result(
    assignments: tuple[tuple[int, ...], ...],
    variable_names: tuple[str, ...],
    form: str,
) -> MinimizationResult | None:
    if not assignments:
        default_expression = "0" if form == "dnf" else "1"
        return MinimizationResult(default_expression, tuple(), tuple(), tuple(), tuple())

    variable_count = len(variable_names)
    if len(assignments) == 2 ** variable_count:
        default_expression = "1" if form == "dnf" else "0"
        full_pattern = tuple(None for _ in variable_names)
        coverage_lines = _build_coverage_table_lines((full_pattern,), assignments, variable_names, form)
        return MinimizationResult(default_expression, (full_pattern,), (full_pattern,), ((full_pattern,),), coverage_lines)
    return None


def _minimize_by_calculation(
    assignments: tuple[tuple[int, ...], ...],
    variable_names: tuple[str, ...],
    form: str,
) -> MinimizationResult:
    constant_result = _minimize_constant_result(assignments, variable_names, form)
    if constant_result is not None:
        return constant_result

    initial_patterns = tuple(assignments)
    gluing_stages, prime_implicants = _build_prime_implicants(initial_patterns)
    selected_implicants = _select_cover(prime_implicants, assignments)
    minimized_expression = _format_minimized_expression(selected_implicants, variable_names, form)
    coverage_lines = _build_coverage_table_lines(selected_implicants, assignments, variable_names, form)
    return MinimizationResult(
        minimized_expression=minimized_expression,
        prime_implicants=prime_implicants,
        selected_implicants=selected_implicants,
        gluing_stages=gluing_stages,
        coverage_table_lines=coverage_lines,
    )


def _minimize_by_table(
    assignments: tuple[tuple[int, ...], ...],
    variable_names: tuple[str, ...],
    form: str,
) -> MinimizationResult:
    constant_result = _minimize_constant_result(assignments, variable_names, form)
    if constant_result is not None:
        return constant_result

    initial_patterns = tuple(assignments)
    gluing_stages, prime_implicants = _build_prime_implicants(initial_patterns)
    selected_implicants = _select_cover_table(prime_implicants, assignments)
    minimized_expression = _format_minimized_expression(selected_implicants, variable_names, form)
    coverage_lines = _build_coverage_table_lines(
        prime_implicants,
        assignments,
        variable_names,
        form,
        selected_implicants=selected_implicants,
    )
    return MinimizationResult(
        minimized_expression=minimized_expression,
        prime_implicants=prime_implicants,
        selected_implicants=selected_implicants,
        gluing_stages=gluing_stages,
        coverage_table_lines=coverage_lines,
    )


def _minimize_by_karnaugh(
    assignments: tuple[tuple[int, ...], ...],
    variable_names: tuple[str, ...],
    form: str,
) -> MinimizationResult:
    constant_result = _minimize_constant_result(assignments, variable_names, form)
    if constant_result is not None:
        return constant_result

    initial_patterns = tuple(assignments)
    gluing_stages, prime_implicants = _build_karnaugh_prime_implicants(initial_patterns, variable_names)
    selected_implicants = _select_cover(prime_implicants, assignments)
    minimized_expression = _format_minimized_expression(selected_implicants, variable_names, form)
    coverage_lines = _build_coverage_table_lines(selected_implicants, assignments, variable_names, form)
    return MinimizationResult(
        minimized_expression=minimized_expression,
        prime_implicants=prime_implicants,
        selected_implicants=selected_implicants,
        gluing_stages=gluing_stages,
        coverage_table_lines=coverage_lines,
    )


def _gray_code(bit_count: int) -> tuple[str, ...]:
    if bit_count == 0:
        return ("",)
    previous = _gray_code(bit_count - 1)
    return tuple("0" + code for code in previous) + tuple("1" + code for code in reversed(previous))


@dataclass
class BooleanFunctionAnalyzer:
    expression_text: str

    def __post_init__(self) -> None:
        self.ast_root: ExpressionNode = parse_expression(self.expression_text)
        self.expression_label = self.ast_root.to_expression_string()
        self.variable_names = tuple(sorted(self.ast_root.collect_variables()))
        if not self.variable_names:
            raise ValueError("Expression must contain at least one variable.")
        if len(self.variable_names) > 5:
            raise ValueError("At most five variables are supported.")
        self.subexpression_nodes = self._collect_unique_subexpressions()
        self.subexpression_labels = tuple(node.to_expression_string() for node in self.subexpression_nodes)
        self.truth_table = self._build_truth_table()

    def _collect_unique_subexpressions(self) -> tuple[ExpressionNode, ...]:
        unique_nodes: list[ExpressionNode] = []
        seen_labels: set[str] = set()
        for subexpression_node in self.ast_root.collect_subexpressions():
            subexpression_label = subexpression_node.to_expression_string()
            if subexpression_label in seen_labels:
                continue
            seen_labels.add(subexpression_label)
            unique_nodes.append(subexpression_node)
        return tuple(unique_nodes)

    def _build_truth_table(self) -> tuple[TruthTableRow, ...]:
        table_rows: list[TruthTableRow] = []
        for bit_values in _iterate_bit_vectors(len(self.variable_names)):
            current_assignment = dict(zip(self.variable_names, bit_values))
            subexpression_values = tuple(
                subexpression_node.evaluate(current_assignment)
                for subexpression_node in self.subexpression_nodes
            )
            result_value = subexpression_values[-1] if subexpression_values else self.ast_root.evaluate(current_assignment)
            table_rows.append(TruthTableRow(tuple(bit_values), subexpression_values, result_value))
        return tuple(table_rows)

    def result_vector(self) -> tuple[int, ...]:
        return tuple(row.result_value for row in self.truth_table)

    def truth_table_lines(self) -> tuple[str, ...]:
        table_rows: list[tuple[str, ...]] = [tuple([*self.variable_names, *self.subexpression_labels])]
        for row in self.truth_table:
            table_rows.append(
                tuple(
                    [
                        *(str(bit_value) for bit_value in row.variable_values),
                        *(str(bit_value) for bit_value in row.subexpression_values),
                    ]
                )
            )
        return _format_table(tuple(table_rows))

    def minterm_indices(self) -> tuple[int, ...]:
        return tuple(index for index, row in enumerate(self.truth_table) if row.result_value == 1)

    def maxterm_indices(self) -> tuple[int, ...]:
        return tuple(index for index, row in enumerate(self.truth_table) if row.result_value == 0)

    def sdnf(self) -> str:
        minterm_patterns = tuple(row.variable_values for row in self.truth_table if row.result_value == 1)
        if not minterm_patterns:
            return "0"
        return " | ".join(_format_dnf_term(bit_pattern, self.variable_names) for bit_pattern in minterm_patterns)

    def sknf(self) -> str:
        maxterm_patterns = tuple(row.variable_values for row in self.truth_table if row.result_value == 0)
        if not maxterm_patterns:
            return "1"
        return " & ".join(_format_cnf_clause(bit_pattern, self.variable_names) for bit_pattern in maxterm_patterns)

    def numeric_forms(self) -> dict[str, tuple[int, ...]]:
        return {
            "sdnf": self.minterm_indices(),
            "sknf": self.maxterm_indices(),
        }

    def index_form(self) -> dict[str, int | str]:
        bit_string = "".join(str(bit_value) for bit_value in self.result_vector())
        return {
            "binary": bit_string,
            "decimal": int(bit_string, 2),
        }

    def zhegalkin_coefficients(self) -> tuple[int, ...]:
        coefficients = list(self.result_vector())
        vector_length = len(coefficients)
        step = 1
        while step < vector_length:
            for start_index in range(vector_length - step):
                if start_index & step == 0:
                    coefficients[start_index + step] ^= coefficients[start_index]
            step <<= 1
        return tuple(coefficients)

    def zhegalkin_polynomial(self) -> str:
        coefficients = self.zhegalkin_coefficients()
        monomials: list[str] = []
        for coefficient_index, coefficient_value in enumerate(coefficients):
            if coefficient_value == 0:
                continue
            if coefficient_index == 0:
                monomials.append("1")
                continue
            monomial_parts = [
                variable_name
                for bit_position, variable_name in enumerate(self.variable_names)
                if (coefficient_index >> (len(self.variable_names) - bit_position - 1)) & 1
            ]
            monomials.append("*".join(monomial_parts))
        return " ^ ".join(monomials) if monomials else "0"

    def _is_linear(self) -> bool:
        for coefficient_index, coefficient_value in enumerate(self.zhegalkin_coefficients()):
            if coefficient_value == 0:
                continue
            if coefficient_index != 0 and bin(coefficient_index).count("1") > 1:
                return False
        return True

    def _is_monotonic(self) -> bool:
        value_map = {row.variable_values: row.result_value for row in self.truth_table}
        for first_assignment in value_map:
            for second_assignment in value_map:
                if all(first_bit <= second_bit for first_bit, second_bit in zip(first_assignment, second_assignment)):
                    if value_map[first_assignment] > value_map[second_assignment]:
                        return False
        return True

    def post_classes(self) -> dict[str, bool]:
        result_vector = self.result_vector()
        preserves_zero = result_vector[0] == 0
        preserves_one = result_vector[-1] == 1
        self_dual = all(
            result_vector[index] != result_vector[-index - 1]
            for index in range(len(result_vector) // 2)
        )
        return {
            "T0": preserves_zero,
            "T1": preserves_one,
            "S": self_dual,
            "L": self._is_linear(),
            "M": self._is_monotonic(),
        }

    def fictive_variables(self) -> tuple[str, ...]:
        fictive_names: list[str] = []
        for variable_index, variable_name in enumerate(self.variable_names):
            is_fictive = True
            for row in self.truth_table:
                flipped_values = list(row.variable_values)
                flipped_values[variable_index] = 1 - flipped_values[variable_index]
                paired_result = self.evaluate_on(tuple(flipped_values))
                if paired_result != row.result_value:
                    is_fictive = False
                    break
            if is_fictive:
                fictive_names.append(variable_name)
        return tuple(fictive_names)

    def evaluate_on(self, bit_values: tuple[int, ...]) -> int:
        assignment = dict(zip(self.variable_names, bit_values))
        return self.ast_root.evaluate(assignment)

    def boolean_derivative(self, derivative_variables: tuple[str, ...]) -> tuple[int, ...]:
        variable_indices = [self.variable_names.index(variable_name) for variable_name in derivative_variables]
        derivative_values: list[int] = []
        for row in self.truth_table:
            derivative_value = 0
            for flip_mask in range(2 ** len(variable_indices)):
                current_values = list(row.variable_values)
                for local_index, variable_index in enumerate(variable_indices):
                    if (flip_mask >> local_index) & 1:
                        current_values[variable_index] ^= 1
                derivative_value ^= self.evaluate_on(tuple(current_values))
            derivative_values.append(derivative_value)
        return tuple(derivative_values)

    def derivative_summary(self) -> dict[str, tuple[int, ...]]:
        summary: dict[str, tuple[int, ...]] = {}
        max_order = min(4, len(self.variable_names))
        for order in range(1, max_order + 1):
            for derivative_variables in combinations(self.variable_names, order):
                summary["d/d" + "".join(derivative_variables)] = self.boolean_derivative(derivative_variables)
        return summary

    def _vector_to_dnf(self, result_vector: tuple[int, ...]) -> str:
        assignments = tuple(
            row.variable_values
            for row, result_value in zip(self.truth_table, result_vector)
            if result_value == 1
        )
        return _minimize_by_calculation(assignments, self.variable_names, "dnf").minimized_expression

    def derivative_formula(self, derivative_variables: tuple[str, ...]) -> str:
        derivative_values = self.boolean_derivative(derivative_variables)
        return self._vector_to_dnf(derivative_values)

    def derivative_report_lines(self) -> tuple[str, ...]:
        report_lines: list[str] = []
        max_order = min(4, len(self.variable_names))
        for order in range(1, max_order + 1):
            for derivative_variables in combinations(self.variable_names, order):
                derivative_name = "d/d" + "".join(derivative_variables)
                derivative_values = self.boolean_derivative(derivative_variables)
                derivative_formula = self._vector_to_dnf(derivative_values)
                report_lines.append(
                    f"{derivative_name}: формула = {derivative_formula}; вектор = {derivative_values}"
                )
        return tuple(report_lines)

    def minimize_dnf_calculation(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 1)
        return _minimize_by_calculation(assignments, self.variable_names, "dnf")

    def minimize_cnf_calculation(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 0)
        return _minimize_by_calculation(assignments, self.variable_names, "cnf")

    def minimize_dnf_calculation_table(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 1)
        return _minimize_by_table(assignments, self.variable_names, "dnf")

    def minimize_cnf_calculation_table(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 0)
        return _minimize_by_table(assignments, self.variable_names, "cnf")

    def karnaugh_map(self, target_value: int) -> tuple[str, ...]:
        variable_count = len(self.variable_names)
        if variable_count > 5:
            raise ValueError("Karnaugh map supports at most five variables.")

        row_count = variable_count // 2
        column_count = variable_count - row_count
        row_codes = _gray_code(row_count)
        column_codes = _gray_code(column_count)

        row_variable_names = "".join(self.variable_names[:row_count]) or "1"
        column_variable_names = "".join(self.variable_names[row_count:]) or "1"
        table_rows: list[tuple[str, ...]] = [
            tuple([f"{row_variable_names}\\{column_variable_names}", *column_codes])
        ]

        for row_code in row_codes:
            cell_values: list[str] = []
            for column_code in column_codes:
                joined_bits = row_code + column_code
                assignment = tuple(int(bit_character) for bit_character in joined_bits) if joined_bits else tuple()
                function_value = self.evaluate_on(assignment)
                cell_values.append(str(int(function_value == target_value)))
            table_rows.append(tuple([row_code or "0", *cell_values]))
        return _format_table(tuple(table_rows))

    def minimize_dnf_karnaugh(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 1)
        return _minimize_by_karnaugh(assignments, self.variable_names, "dnf")

    def minimize_cnf_karnaugh(self) -> MinimizationResult:
        assignments = tuple(row.variable_values for row in self.truth_table if row.result_value == 0)
        return _minimize_by_karnaugh(assignments, self.variable_names, "cnf")

    def build_report(self) -> str:
        report_sections: list[str] = []
        report_sections.append("Выражение: " + self.expression_text)
        report_sections.append("Переменные: " + ", ".join(self.variable_names))
        report_sections.append("Таблица истинности:\n" + "\n".join(self.truth_table_lines()))
        report_sections.append("СДНФ: " + self.sdnf())
        report_sections.append("СКНФ: " + self.sknf())
        report_sections.append("Числовые формы: " + str(self.numeric_forms()))
        report_sections.append("Индексная форма: " + str(self.index_form()))
        report_sections.append("Классы Поста: " + str(self.post_classes()))
        report_sections.append("Полином Жегалкина: " + self.zhegalkin_polynomial())
        report_sections.append("Фиктивные переменные: " + (", ".join(self.fictive_variables()) or "нет"))
        report_sections.append("Булевы производные:\n" + "\n".join(self.derivative_report_lines()))

        dnf_result = self.minimize_dnf_calculation()
        cnf_result = self.minimize_cnf_calculation()
        dnf_table_result = self.minimize_dnf_calculation_table()
        cnf_table_result = self.minimize_cnf_calculation_table()
        report_sections.append("Минимизация ДНФ расчетным методом: " + dnf_result.minimized_expression)
        report_sections.append("Минимизация КНФ расчетным методом: " + cnf_result.minimized_expression)
        report_sections.append("Минимизация ДНФ расчетно-табличным методом: " + dnf_table_result.minimized_expression)
        report_sections.append("Минимизация КНФ расчетно-табличным методом: " + cnf_table_result.minimized_expression)
        report_sections.append("Таблица покрытия для ДНФ:\n" + "\n".join(dnf_table_result.coverage_table_lines or ("пусто",)))
        report_sections.append("Таблица покрытия для КНФ:\n" + "\n".join(cnf_table_result.coverage_table_lines or ("пусто",)))
        report_sections.append("Карта Карно для ДНФ:\n" + "\n".join(self.karnaugh_map(1)))
        report_sections.append("Карта Карно для КНФ:\n" + "\n".join(self.karnaugh_map(0)))
        report_sections.append("Минимизация ДНФ по карте Карно: " + self.minimize_dnf_karnaugh().minimized_expression)
        report_sections.append("Минимизация КНФ по карте Карно: " + self.minimize_cnf_karnaugh().minimized_expression)
        return "\n\n".join(report_sections)
