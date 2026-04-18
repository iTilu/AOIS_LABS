import pytest

import boolean_analysis
import logic_parser
from boolean_analysis import BooleanFunctionAnalyzer
from logic_parser import BinaryNode, UnaryNode, VariableNode, normalize_expression, parse_expression


def test_normalize_expression_replaces_unicode_symbols():
    assert normalize_expression(" !(!a→!b)∨c ") == "!(!a->!b)|c"


def test_parse_expression_builds_ast_and_respects_precedence():
    parsed_expression = parse_expression("a|b&!c")
    assert isinstance(parsed_expression, BinaryNode)
    assert parsed_expression.operator == "|"
    assert isinstance(parsed_expression.right_operand, BinaryNode)
    assert parsed_expression.right_operand.operator == "&"
    assert isinstance(parsed_expression.right_operand.right_operand, UnaryNode)
    assert isinstance(parsed_expression.left_operand, VariableNode)


def test_parse_expression_rejects_invalid_variable():
    with pytest.raises(ValueError):
        parse_expression("x&y")


def test_truth_table_and_normal_forms_for_implication_with_or():
    analyzer = BooleanFunctionAnalyzer("!(!a->!b)|c")

    assert analyzer.variable_names == ("a", "b", "c")
    assert analyzer.result_vector() == (0, 1, 1, 1, 0, 1, 0, 1)
    assert analyzer.sdnf() == "!a&!b&c | !a&b&!c | !a&b&c | a&!b&c | a&b&c"
    assert analyzer.sknf() == "(a|b|c) & (!a|b|c) & (!a|!b|c)"
    assert analyzer.numeric_forms() == {"sdnf": (1, 2, 3, 5, 7), "sknf": (0, 4, 6)}
    assert analyzer.index_form() == {"binary": "01110101", "decimal": 117}


def test_post_classes_and_fictive_variables():
    analyzer = BooleanFunctionAnalyzer("a")
    assert analyzer.post_classes() == {"T0": True, "T1": True, "S": True, "L": True, "M": True}
    assert analyzer.fictive_variables() == ()

    analyzer_with_fictive = BooleanFunctionAnalyzer("a|(b&!b)")
    assert analyzer_with_fictive.variable_names == ("a", "b")
    assert analyzer_with_fictive.fictive_variables() == ("b",)


def test_zhegalkin_polynomial_for_xor():
    analyzer = BooleanFunctionAnalyzer("(!a&b)|(a&!b)")
    assert analyzer.result_vector() == (0, 1, 1, 0)
    assert analyzer.zhegalkin_coefficients() == (0, 1, 1, 0)
    assert analyzer.zhegalkin_polynomial() == "b ^ a"
    assert analyzer.post_classes()["L"] is True


def test_boolean_derivatives_for_and_function():
    analyzer = BooleanFunctionAnalyzer("a&b")
    assert analyzer.boolean_derivative(("a",)) == (0, 1, 0, 1)
    assert analyzer.boolean_derivative(("b",)) == (0, 0, 1, 1)
    assert analyzer.boolean_derivative(("a", "b")) == (1, 1, 1, 1)
    assert analyzer.derivative_formula(("a",)) == "b"
    assert analyzer.derivative_formula(("b",)) == "a"
    assert analyzer.derivative_formula(("a", "b")) == "1"

    summary = analyzer.derivative_summary()
    assert summary["d/da"] == (0, 1, 0, 1)
    assert summary["d/dab"] == (1, 1, 1, 1)


def test_dnf_minimization_and_coverage_table():
    analyzer = BooleanFunctionAnalyzer("(!a&b&c)|(a&!b&!c)|(a&!b&c)|(a&b&!c)|(a&b&c)")
    minimization_result = analyzer.minimize_dnf_calculation()

    assert minimization_result.minimized_expression == "a | b&c"
    assert minimization_result.selected_implicants == ((1, None, None), (None, 1, 1))
    assert len(minimization_result.gluing_stages) >= 2
    assert minimization_result.coverage_table_lines[0].startswith("Импликанта")
    assert "a" in minimization_result.coverage_table_lines[2]


def test_cnf_minimization_for_or_function():
    analyzer = BooleanFunctionAnalyzer("a|b")
    minimization_result = analyzer.minimize_cnf_calculation()

    assert minimization_result.minimized_expression == "(a|b)"
    assert minimization_result.selected_implicants == ((0, 0),)
    assert minimization_result.coverage_table_lines[-1].startswith("(a|b)")


def test_constant_like_edge_cases_in_minimization():
    analyzer_false = BooleanFunctionAnalyzer("a&!a")
    assert analyzer_false.sdnf() == "0"
    assert analyzer_false.minimize_dnf_calculation().minimized_expression == "0"
    assert analyzer_false.minimize_cnf_calculation().minimized_expression == "0"

    analyzer_true = BooleanFunctionAnalyzer("a|!a")
    assert analyzer_true.sknf() == "1"
    assert analyzer_true.minimize_dnf_calculation().minimized_expression == "1"
    assert analyzer_true.minimize_cnf_calculation().minimized_expression == "1"


def test_karnaugh_map_and_matching_minimization():
    analyzer = BooleanFunctionAnalyzer("a&b|a&c")
    karnaugh_lines = analyzer.karnaugh_map(1)
    assert karnaugh_lines[0].startswith("a\\bc")
    assert analyzer.minimize_dnf_karnaugh().minimized_expression == "a&b | a&c"
    assert analyzer.minimize_cnf_karnaugh().minimized_expression == "(a) & (b|c)"


def test_truth_table_lines_and_build_report():
    analyzer = BooleanFunctionAnalyzer("a->b")
    truth_lines = analyzer.truth_table_lines()
    assert truth_lines[0] == "a | b | (a->b)"
    assert truth_lines[1] == "_ | _ | ______"
    assert truth_lines[-1] == "1 | 1 | 1     "

    report_text = analyzer.build_report()
    assert "Таблица истинности:" in report_text
    assert "Полином Жегалкина:" in report_text
    assert "Карта Карно для ДНФ:" in report_text
    assert "Булевы производные:" in report_text
    assert "формула =" in report_text
    assert "Минимизация ДНФ расчетно-табличным методом:" in report_text
    assert "Минимизация КНФ расчетно-табличным методом:" in report_text


def test_truth_table_contains_subexpressions():
    analyzer = BooleanFunctionAnalyzer("!(!a->!b)|c")
    truth_lines = analyzer.truth_table_lines()
    assert "!a" in truth_lines[0]
    assert "!b" in truth_lines[0]
    assert "(!a->!b)" in truth_lines[0]
    assert "!(!a->!b)" in truth_lines[0]
    assert "(!(!a->!b)|c)" in truth_lines[0]


def test_parser_and_node_error_branches():
    with pytest.raises(ValueError, match="Expression cannot be empty"):
        parse_expression("")

    with pytest.raises(ValueError, match="Missing closing parenthesis"):
        parse_expression("(a|b")

    with pytest.raises(ValueError, match="Unexpected end of expression"):
        parse_expression("!")

    with pytest.raises(ValueError, match="Unexpected token"):
        parse_expression("ab")

    base_node = logic_parser.ExpressionNode()
    with pytest.raises(NotImplementedError):
        base_node.evaluate({})
    with pytest.raises(NotImplementedError):
        base_node.collect_variables()
    with pytest.raises(NotImplementedError):
        base_node.to_expression_string()
    with pytest.raises(NotImplementedError):
        base_node.collect_subexpressions()

    unsupported_unary = UnaryNode("?", VariableNode("a"))
    with pytest.raises(ValueError, match="Unsupported unary operator"):
        unsupported_unary.evaluate({"a": 1})

    unsupported_binary = BinaryNode("?", VariableNode("a"), VariableNode("b"))
    with pytest.raises(ValueError, match="Unsupported binary operator"):
        unsupported_binary.evaluate({"a": 1, "b": 0})


def test_parser_handles_equivalence_and_peek_end():
    analyzer = BooleanFunctionAnalyzer("a~b")
    assert analyzer.result_vector() == (1, 0, 0, 1)
    parser = logic_parser.ExpressionParser("a")
    assert parser._peek() == "a"
    parser.position = 1
    assert parser._peek() is None


def test_internal_helpers_and_cover_selection():
    assert boolean_analysis._format_table(tuple()) == tuple()
    assert boolean_analysis._combine_patterns((1, None), (1, 0)) is None
    assert boolean_analysis._combine_patterns((1, 0), (0, 1)) is None
    assert boolean_analysis._combine_patterns((1, 0), (1, 0)) is None
    assert boolean_analysis._all_assignments_covered(((1, None),), ((0, 0),)) is False
    assert boolean_analysis._build_coverage_table_lines(tuple(), ((0, 0),), ("a", "b"), "dnf") == tuple()
    assert boolean_analysis._format_dnf_term((None, None), ("a", "b")) == "1"
    assert boolean_analysis._format_cnf_clause((None, None), ("a", "b")) == "0"

    prime_implicants = ((0, None), (None, 0), (1, None), (None, 1))
    required_assignments = ((0, 0), (0, 1), (1, 0), (1, 1))
    selected_implicants = boolean_analysis._select_cover(prime_implicants, required_assignments)
    assert selected_implicants in (((0, None), (1, None)), ((None, 0), (None, 1)))
    assert boolean_analysis._select_cover(prime_implicants, tuple()) == tuple()


def test_minimization_wrappers_and_edge_reports():
    analyzer = BooleanFunctionAnalyzer("a|b")
    assert analyzer.minimize_dnf_calculation_table().minimized_expression == analyzer.minimize_dnf_calculation().minimized_expression
    assert analyzer.minimize_cnf_calculation_table().minimized_expression == analyzer.minimize_cnf_calculation().minimized_expression

    false_report = BooleanFunctionAnalyzer("a&!a").build_report()
    true_report = BooleanFunctionAnalyzer("a|!a").build_report()
    assert "Таблица покрытия для ДНФ:\nпусто" in false_report
    assert "Таблица покрытия для КНФ:\nпусто" in true_report


def test_post_init_validation_and_karnaugh_limit(monkeypatch):
    class FakeNode:
        def collect_variables(self):
            return set()

        def to_expression_string(self):
            return "fake"

        def collect_subexpressions(self):
            return tuple()

        def evaluate(self, variable_values):
            return 0

    monkeypatch.setattr(boolean_analysis, "parse_expression", lambda expression_text: FakeNode())
    with pytest.raises(ValueError, match="at least one variable"):
        BooleanFunctionAnalyzer("a")

    class TooManyVariablesNode(FakeNode):
        def collect_variables(self):
            return {"a", "b", "c", "d", "e", "ab"}

    monkeypatch.setattr(boolean_analysis, "parse_expression", lambda expression_text: TooManyVariablesNode())
    with pytest.raises(ValueError, match="At most five variables"):
        BooleanFunctionAnalyzer("a")

    analyzer = object.__new__(BooleanFunctionAnalyzer)
    analyzer.variable_names = ("a", "b", "c", "d", "e", "ab")
    with pytest.raises(ValueError, match="at most five variables"):
        analyzer.karnaugh_map(1)
