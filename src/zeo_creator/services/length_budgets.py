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


class LengthBudgetInputError(ValueError):
    """The document is not a `length-budgets/1` object. The message is a fixed phrase."""


_KEYS = {
    "budgets",
    "sections",
    "subject",
    "subject_max_chars",
    "preheader",
    "preheader_max_chars",
    "overall_max_words",
}


def _whole(value: object, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise LengthBudgetInputError("a number in the document is not a whole number in range")
    return value


def check_length_budgets_input(document: object) -> tuple[str, ...]:
    """Check a `length-budgets/1` object: the same check, for a caller without Python.

    Shape: {"budgets": {name: [min, max]}, "sections": {name: text or [text, ...]},
    "subject", "subject_max_chars", "preheader", "preheader_max_chars",
    "overall_max_words"}; only `budgets` and `sections` are required. A malformed document
    raises LengthBudgetInputError with a fixed message that never quotes the input.
    """
    if not isinstance(document, dict):
        raise LengthBudgetInputError("the document is not a JSON object")
    if not _KEYS.issuperset(document):
        raise LengthBudgetInputError("the document has a key that length-budgets/1 does not define")
    raw_budgets, raw_sections = document.get("budgets"), document.get("sections")
    if not isinstance(raw_budgets, dict) or not isinstance(raw_sections, dict):
        raise LengthBudgetInputError("budgets and sections must both be JSON objects")
    budgets: dict[str, tuple[int, int]] = {}
    for name, pair in raw_budgets.items():
        if not isinstance(pair, list) or len(pair) != 2:
            raise LengthBudgetInputError("each budget must be a [minimum, maximum] pair")
        low, high = _whole(pair[0], minimum=0), _whole(pair[1], minimum=0)
        if low > high:
            raise LengthBudgetInputError("a budget minimum is above its maximum")
        budgets[name] = (low, high)
    sections: dict[str, str | list[str]] = {}
    for name, value in raw_sections.items():
        texts = [value] if isinstance(value, str) else value
        if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
            raise LengthBudgetInputError("each section must be a string or a list of strings")
        sections[name] = value
    text_fields: dict[str, str | None] = {}
    for key in ("subject", "preheader"):
        value = document.get(key)
        if value is not None and not isinstance(value, str):
            raise LengthBudgetInputError("subject and preheader must be strings")
        text_fields[key] = value
    limits: dict[str, int | None] = {}
    for key in ("subject_max_chars", "preheader_max_chars", "overall_max_words"):
        value = document.get(key)
        limits[key] = None if value is None else _whole(value, minimum=0)
    return check_length_budgets(
        budgets=budgets,
        sections=sections,
        subject=text_fields["subject"],
        subject_max_chars=limits["subject_max_chars"],
        preheader=text_fields["preheader"],
        preheader_max_chars=limits["preheader_max_chars"],
        overall_max_words=limits["overall_max_words"],
    )
