import pytest

from hash_table import HashTableItem, LinearProbingHashTable


def test_hash_function_uses_character_codes_mod_capacity():
    table = LinearProbingHashTable(capacity=10)
    assert table.key_value("Вяткин") == 2 * 33 + 32
    assert table.key_value("Третьяк") == 19 * 33 + 17
    assert table.hash("Вяткин") == 98 % 10


def test_create_and_read_value():
    table = LinearProbingHashTable(capacity=4)
    table.create("Алгебра", "раздел математики")

    assert table.read("Алгебра") == "раздел математики"
    assert table.size == 1


def test_create_rejects_duplicate_key():
    table = LinearProbingHashTable(capacity=4)
    table.create("Физика", 1)

    with pytest.raises(KeyError, match="Key already exists"):
        table.create("Физика", 2)


def test_update_existing_value():
    table = LinearProbingHashTable(capacity=4)
    table.create("Химия", 1)
    table.update("Химия", 2)

    assert table.read("Химия") == 2
    assert table.size == 1


def test_delete_existing_value():
    table = LinearProbingHashTable(capacity=4)
    table.create("Биология", 1)
    table.delete("Биология")

    assert table.size == 0
    with pytest.raises(KeyError, match="Key not found"):
        table.read("Биология")


def test_read_update_delete_missing_key_raise_key_error():
    table = LinearProbingHashTable(capacity=4)

    with pytest.raises(KeyError, match="Key not found"):
        table.read("Геометрия")
    with pytest.raises(KeyError, match="Key not found"):
        table.update("Геометрия", 42)
    with pytest.raises(KeyError, match="Key not found"):
        table.delete("Геометрия")


def test_linear_probing_resolves_collisions():
    table = LinearProbingHashTable(capacity=8)
    assert table.hash("Анализ") == table.hash("Аэробика")

    table.create("Анализ", "first")
    table.create("Аэробика", "second")

    assert table.read("Анализ") == "first"
    assert table.read("Аэробика") == "second"
    assert table.size == 2


def test_deleted_slot_does_not_break_collision_chain_and_can_be_reused():
    table = LinearProbingHashTable(capacity=8)
    table.create("Анализ", "first")
    table.create("Аэробика", "second")
    table.create("Ахроматизм", "third")

    table.delete("Анализ")

    assert table.read("Аэробика") == "second"
    assert table.read("Ахроматизм") == "third"

    table.create("Аёлка", "new")
    assert table.read("Аёлка") == "new"
    assert table.size == 3


def test_full_table_raises_overflow_error():
    table = LinearProbingHashTable(capacity=2)

    table.create("Алгебра", 1)
    table.create("Биология", 2)

    with pytest.raises(OverflowError, match="Hash table is full"):
        table.create("Геометрия", 3)


def test_contains_and_items():
    table = LinearProbingHashTable(capacity=4)
    table.create("Алгебра", 1)
    table.create("Биология", 2)

    assert table.contains("Алгебра") is True
    assert table.contains("Геометрия") is False
    assert set(table.items()) == {HashTableItem("Алгебра", 1), HashTableItem("Биология", 2)}


def test_key_validation():
    table = LinearProbingHashTable(capacity=4)

    with pytest.raises(ValueError, match="Capacity must be positive"):
        LinearProbingHashTable(capacity=0)
    with pytest.raises(ValueError, match="at least two letters"):
        table.create("А", 1)
    with pytest.raises(ValueError, match="Russian alphabet"):
        table.create("ab", 1)
    with pytest.raises(TypeError, match="Key must be a string"):
        table.create(123, 1)
