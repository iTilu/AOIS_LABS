from __future__ import annotations

from dataclasses import dataclass


def normalize_expression(source_text: str) -> str:
    normalized_text = source_text.strip().replace(" ", "")
    replacements = {
        "¬": "!",
        "∧": "&",
        "∨": "|",
        "→": "->",
    }
    for source_symbol, target_symbol in replacements.items():
        normalized_text = normalized_text.replace(source_symbol, target_symbol)
    return normalized_text


class ExpressionNode:
    def evaluate(self, variable_values: dict[str, int]) -> int:
        raise NotImplementedError

    def collect_variables(self) -> set[str]:
        raise NotImplementedError

    def to_expression_string(self) -> str:
        raise NotImplementedError

    def collect_subexpressions(self) -> tuple["ExpressionNode", ...]:
        raise NotImplementedError


@dataclass(frozen=True)
class VariableNode(ExpressionNode):
    name: str

    def evaluate(self, variable_values: dict[str, int]) -> int:
        return int(variable_values[self.name])

    def collect_variables(self) -> set[str]:
        return {self.name}

    def to_expression_string(self) -> str:
        return self.name

    def collect_subexpressions(self) -> tuple["ExpressionNode", ...]:
        return tuple()


@dataclass(frozen=True)
class UnaryNode(ExpressionNode):
    operator: str
    operand: ExpressionNode

    def evaluate(self, variable_values: dict[str, int]) -> int:
        operand_value = self.operand.evaluate(variable_values)
        if self.operator == "!":
            return 1 - operand_value
        raise ValueError(f"Unsupported unary operator: {self.operator}")

    def collect_variables(self) -> set[str]:
        return self.operand.collect_variables()

    def to_expression_string(self) -> str:
        operand_text = self.operand.to_expression_string()
        if isinstance(self.operand, (VariableNode, BinaryNode)):
            return f"{self.operator}{operand_text}"
        return f"{self.operator}({operand_text})"

    def collect_subexpressions(self) -> tuple["ExpressionNode", ...]:
        return (*self.operand.collect_subexpressions(), self)


@dataclass(frozen=True)
class BinaryNode(ExpressionNode):
    operator: str
    left_operand: ExpressionNode
    right_operand: ExpressionNode

    def evaluate(self, variable_values: dict[str, int]) -> int:
        left_value = self.left_operand.evaluate(variable_values)
        right_value = self.right_operand.evaluate(variable_values)

        if self.operator == "&":
            return left_value & right_value
        if self.operator == "|":
            return left_value | right_value
        if self.operator == "->":
            return int((not left_value) or right_value)
        if self.operator == "~":
            return int(left_value == right_value)
        raise ValueError(f"Unsupported binary operator: {self.operator}")

    def collect_variables(self) -> set[str]:
        return self.left_operand.collect_variables() | self.right_operand.collect_variables()

    def to_expression_string(self) -> str:
        left_text = self.left_operand.to_expression_string()
        right_text = self.right_operand.to_expression_string()
        return f"({left_text}{self.operator}{right_text})"

    def collect_subexpressions(self) -> tuple["ExpressionNode", ...]:
        return (
            *self.left_operand.collect_subexpressions(),
            *self.right_operand.collect_subexpressions(),
            self,
        )


class ExpressionParser:
    def __init__(self, expression_text: str):
        self.expression_text = normalize_expression(expression_text)
        self.position = 0

    def parse(self) -> ExpressionNode:
        if not self.expression_text:
            raise ValueError("Expression cannot be empty.")

        parsed_node = self._parse_equivalence()
        if self.position != len(self.expression_text):
            raise ValueError(f"Unexpected token at position {self.position}.")
        return parsed_node

    def _peek(self) -> str | None:
        if self.position >= len(self.expression_text):
            return None
        return self.expression_text[self.position]

    def _match(self, token_text: str) -> bool:
        if self.expression_text.startswith(token_text, self.position):
            self.position += len(token_text)
            return True
        return False

    def _parse_equivalence(self) -> ExpressionNode:
        left_node = self._parse_implication()
        while self._match("~"):
            right_node = self._parse_implication()
            left_node = BinaryNode("~", left_node, right_node)
        return left_node

    def _parse_implication(self) -> ExpressionNode:
        left_node = self._parse_disjunction()
        if self._match("->"):
            right_node = self._parse_implication()
            return BinaryNode("->", left_node, right_node)
        return left_node

    def _parse_disjunction(self) -> ExpressionNode:
        left_node = self._parse_conjunction()
        while self._match("|"):
            right_node = self._parse_conjunction()
            left_node = BinaryNode("|", left_node, right_node)
        return left_node

    def _parse_conjunction(self) -> ExpressionNode:
        left_node = self._parse_unary()
        while self._match("&"):
            right_node = self._parse_unary()
            left_node = BinaryNode("&", left_node, right_node)
        return left_node

    def _parse_unary(self) -> ExpressionNode:
        if self._match("!"):
            return UnaryNode("!", self._parse_unary())
        if self._match("("):
            nested_node = self._parse_equivalence()
            if not self._match(")"):
                raise ValueError("Missing closing parenthesis.")
            return nested_node

        current_symbol = self._peek()
        if current_symbol is None:
            raise ValueError("Unexpected end of expression.")
        if current_symbol not in "abcde":
            raise ValueError(f"Unsupported variable '{current_symbol}'.")
        self.position += 1
        return VariableNode(current_symbol)


def parse_expression(expression_text: str) -> ExpressionNode:
    return ExpressionParser(expression_text).parse()
