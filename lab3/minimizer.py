from __future__ import annotations

from dataclasses import dataclass


BitTuple = tuple[int, ...]
MaskTuple = tuple[int | None, ...]


@dataclass(frozen=True)
class MinimizationResult:
    expression: str
    prime_implicants: tuple[MaskTuple, ...]
    selected_implicants: tuple[MaskTuple, ...]


def _count_defined_bits(mask: MaskTuple) -> int:
    return sum(bit is not None for bit in mask)


def _mask_sort_key(mask: MaskTuple) -> tuple[int, tuple[int, ...]]:
    normalized = tuple(-1 if bit is None else bit for bit in mask)
    return (_count_defined_bits(mask), normalized)


def _combine_masks(first: MaskTuple, second: MaskTuple) -> MaskTuple | None:
    mismatch_count = 0
    combined: list[int | None] = []

    for left_bit, right_bit in zip(first, second):
        if left_bit == right_bit:
            combined.append(left_bit)
            continue
        if left_bit is None or right_bit is None:
            return None
        mismatch_count += 1
        combined.append(None)
        if mismatch_count > 1:
            return None

    if mismatch_count != 1:
        return None
    return tuple(combined)


def _mask_covers(mask: MaskTuple, values: BitTuple) -> bool:
    return all(expected is None or expected == actual for expected, actual in zip(mask, values))


def _build_prime_implicants(minterms: tuple[BitTuple, ...], dont_cares: tuple[BitTuple, ...]) -> tuple[MaskTuple, ...]:
    current_level = tuple(sorted(set((*minterms, *dont_cares)), key=_mask_sort_key))
    prime_implicants: set[MaskTuple] = set()

    while current_level:
        used_masks: set[MaskTuple] = set()
        next_level: set[MaskTuple] = set()

        for first_index, first_mask in enumerate(current_level):
            for second_mask in current_level[first_index + 1 :]:
                combined = _combine_masks(first_mask, second_mask)
                if combined is None:
                    continue
                used_masks.add(first_mask)
                used_masks.add(second_mask)
                next_level.add(combined)

        for current_mask in current_level:
            if current_mask in used_masks:
                continue
            if any(_mask_covers(current_mask, minterm) for minterm in minterms):
                prime_implicants.add(current_mask)

        if not next_level:
            break
        current_level = tuple(sorted(next_level, key=_mask_sort_key))

    return tuple(sorted(prime_implicants, key=_mask_sort_key))


def _select_implicants(prime_implicants: tuple[MaskTuple, ...], minterms: tuple[BitTuple, ...]) -> tuple[MaskTuple, ...]:
    if not minterms:
        return tuple()

    uncovered = set(minterms)
    selected_indices: set[int] = set()

    for minterm in minterms:
        covering_indices = [
            index for index, implicant in enumerate(prime_implicants) if _mask_covers(implicant, minterm)
        ]
        if len(covering_indices) != 1:
            continue
        selected_indices.add(covering_indices[0])

    for index in selected_indices:
        implicant = prime_implicants[index]
        uncovered = {minterm for minterm in uncovered if not _mask_covers(implicant, minterm)}

    while uncovered:
        best_index = max(
            (index for index in range(len(prime_implicants)) if index not in selected_indices),
            key=lambda index: (
                sum(1 for minterm in uncovered if _mask_covers(prime_implicants[index], minterm)),
                -_count_defined_bits(prime_implicants[index]),
                tuple(-1 if bit is None else bit for bit in prime_implicants[index]),
            ),
        )
        selected_indices.add(best_index)
        implicant = prime_implicants[best_index]
        uncovered = {minterm for minterm in uncovered if not _mask_covers(implicant, minterm)}

    return tuple(sorted((prime_implicants[index] for index in selected_indices), key=_mask_sort_key))


def _format_implicant(mask: MaskTuple, variable_names: tuple[str, ...]) -> str:
    if all(bit is None for bit in mask):
        return "1"

    terms: list[str] = []
    for variable_name, bit in zip(variable_names, mask):
        if bit is None:
            continue
        terms.append(variable_name if bit == 1 else f"!{variable_name}")
    return " & ".join(terms)


def minimize_sdnf(
    variable_names: tuple[str, ...],
    minterms: tuple[BitTuple, ...],
    dont_cares: tuple[BitTuple, ...] = tuple(),
) -> MinimizationResult:
    if not minterms:
        return MinimizationResult(expression="0", prime_implicants=tuple(), selected_implicants=tuple())

    if len(minterms) == 2 ** len(variable_names):
        universal_mask = tuple(None for _ in variable_names)
        return MinimizationResult(expression="1", prime_implicants=(universal_mask,), selected_implicants=(universal_mask,))

    prime_implicants = _build_prime_implicants(minterms, dont_cares)
    selected_implicants = _select_implicants(prime_implicants, minterms)
    expression = " | ".join(_format_implicant(mask, variable_names) for mask in selected_implicants)
    return MinimizationResult(
        expression=expression,
        prime_implicants=prime_implicants,
        selected_implicants=selected_implicants,
    )
