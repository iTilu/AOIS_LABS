from hash_table import LinearProbingHashTable


def print_table(table: LinearProbingHashTable) -> None:
    print(f"Размер: {table.size}, вместимость: {table.capacity}")
    for item in table.items():
        print(f"{item.key}: V={table.key_value(item.key)}, h={table.hash(item.key)}, данные={item.value}")


def main() -> None:
    table = LinearProbingHashTable()
    actions = {
        "1": "Создать запись",
        "2": "Прочитать запись",
        "3": "Обновить запись",
        "4": "Удалить запись",
        "5": "Показать таблицу",
        "0": "Выход",
    }

    while True:
        print("\nХЕШ-ТАБЛИЦА С ПОСЛЕДОВАТЕЛЬНЫМ ПОИСКОМ")
        for action_number, action_text in actions.items():
            print(f"{action_number}. {action_text}")

        selected_action = input("Выберите действие: ").strip()
        try:
            if selected_action == "1":
                table.create(input("Ключ: ").strip(), input("Значение: ").strip())
            elif selected_action == "2":
                print(table.read(input("Ключ: ").strip()))
            elif selected_action == "3":
                table.update(input("Ключ: ").strip(), input("Новое значение: ").strip())
            elif selected_action == "4":
                table.delete(input("Ключ: ").strip())
            elif selected_action == "5":
                print_table(table)
            elif selected_action == "0":
                break
            else:
                print("Неизвестное действие.")
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
