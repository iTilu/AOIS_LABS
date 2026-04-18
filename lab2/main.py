from boolean_analysis import BooleanFunctionAnalyzer


def main() -> None:
    expression_text = input("Введите логическую функцию: ").strip()
    analyzer = BooleanFunctionAnalyzer(expression_text)
    print(analyzer.build_report())


if __name__ == "__main__":
    main()
