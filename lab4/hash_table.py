from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
ALPHABET_BASE = len(RUSSIAN_ALPHABET)
LETTER_VALUES = {letter: letter_index for letter_index, letter in enumerate(RUSSIAN_ALPHABET)}


@dataclass(frozen=True)
class HashTableItem:
    key: str
    value: Any


class LinearProbingHashTable:
    _DELETED = object()

    def __init__(self, capacity: int = 16) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self._items: list[HashTableItem | object | None] = [None] * capacity
        self._size = 0
        self._deleted_count = 0

    @property
    def capacity(self) -> int:
        return len(self._items)

    @property
    def size(self) -> int:
        return self._size

    def hash(self, key: str) -> int:
        return self.key_value(key) % self.capacity

    def key_value(self, key: str) -> int:
        self._validate_key(key)
        first_letter, second_letter = key.upper()[:2]
        return LETTER_VALUES[first_letter] * ALPHABET_BASE + LETTER_VALUES[second_letter]

    def create(self, key: str, value: Any) -> None:
        self._validate_key(key)
        item_index, found = self._find_slot(key, for_insert=True)
        if found:
            raise KeyError(f"Key already exists: {key}")

        if self._items[item_index] is self._DELETED:
            self._deleted_count -= 1
        self._items[item_index] = HashTableItem(key, value)
        self._size += 1

    def read(self, key: str) -> Any:
        item_index, found = self._find_slot(key, for_insert=False)
        if not found:
            raise KeyError(f"Key not found: {key}")
        item = self._items[item_index]
        assert isinstance(item, HashTableItem)
        return item.value

    def update(self, key: str, value: Any) -> None:
        item_index, found = self._find_slot(key, for_insert=False)
        if not found:
            raise KeyError(f"Key not found: {key}")
        self._items[item_index] = HashTableItem(key, value)

    def delete(self, key: str) -> None:
        item_index, found = self._find_slot(key, for_insert=False)
        if not found:
            raise KeyError(f"Key not found: {key}")
        self._items[item_index] = self._DELETED
        self._size -= 1
        self._deleted_count += 1

    def contains(self, key: str) -> bool:
        return self._find_slot(key, for_insert=False)[1]

    def items(self) -> tuple[HashTableItem, ...]:
        return tuple(item for item in self._items if isinstance(item, HashTableItem))

    def _find_slot(self, key: str, for_insert: bool) -> tuple[int, bool]:
        self._validate_key(key)
        start_index = self.hash(key)
        first_deleted_index: int | None = None

        for step in range(self.capacity):
            item_index = (start_index + step) % self.capacity
            item = self._items[item_index]

            if item is None:
                if for_insert and first_deleted_index is not None:
                    return first_deleted_index, False
                return item_index, False

            if item is self._DELETED:
                if for_insert and first_deleted_index is None:
                    first_deleted_index = item_index
                continue

            assert isinstance(item, HashTableItem)
            if item.key == key:
                return item_index, True

        if for_insert and first_deleted_index is not None:
            return first_deleted_index, False
        raise OverflowError("Hash table is full")

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        if len(key) < 2:
            raise ValueError("Key must contain at least two letters")
        unknown_letters = [letter for letter in key.upper()[:2] if letter not in LETTER_VALUES]
        if unknown_letters:
            raise ValueError("First two key letters must belong to the Russian alphabet")
