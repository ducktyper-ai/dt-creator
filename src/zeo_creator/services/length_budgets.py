"""A generic, deterministic word-budget check for drafted text.

The caller supplies every budget; nothing here knows a property, a format or a policy. It
names each budget a draft breaks and never trims, so a section over budget fails loudly.
"""

import re
from collections.abc import Mapping, Sequence

_URL = re.compile(r"https?://\S+")


def words(text: str) -> int:
    """Words of the plain alternative, URLs excluded."""
    return len(_URL.sub(" ", text).split())


def check_length_budgets(
    *,
    budgets: Mapping[str, tuple[int, int]],
    sections: Mapping[str, str | Sequence[str]],
    subject: str | None = None,
    subject_max_chars: int | None = None,
    preheader: str | None = None,
    preheader_max_chars: int | None = None,
    overall_max_words: int | None = None,
) -> tuple[str, ...]:
    """Name every budget a draft breaks; empty means within budget.

    `budgets` maps a section name to (minimum words, maximum words) per item. A list-valued
    section is checked item by item, and a section with no declared budget is a breach.
    """
    broken: list[str] = []
    if subject is not None and subject_max_chars is not None and len(subject) > subject_max_chars:
        broken.append(f"subject: {len(subject)} characters, at most {subject_max_chars}")
    if (
        preheader is not None
        and preheader_max_chars is not None
        and len(preheader) > preheader_max_chars
    ):
        broken.append(f"preheader: {len(preheader)} characters, at most {preheader_max_chars}")
    total = 0
    for name, value in sections.items():
        items = [value] if isinstance(value, str) else value
        if name not in budgets:
            total += sum(words(text) for text in items)
            broken.append(f"{name}: no budget declared")
            continue
        low, high = budgets[name]
        for index, text in enumerate(items, start=1):
            count = words(text)
            total += count
            if not low <= count <= high:
                broken.append(f"{name} {index}: {count} words, expected {low} to {high}")
    if overall_max_words is not None and total > overall_max_words:
        broken.append(f"overall: {total} words, at most {overall_max_words}")
    return tuple(broken)
