"""Deterministic structural lint for a post thread (a numbered series of short posts).

Pure and offline: no model, provider or network call, and no house word list. It checks what
a program can prove (length, numbering, source placement, links, repetition) and names what
it cannot (meaning, hook quality, one idea per thread) under ``needs_review`` for a human or
a runner-side reviewer. A caller may supply its own forbidden phrases; none ship here.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from zeo_creator import __version__

POST_LIMIT = 280
URL_WEIGHT = 23
MAX_POSTS = 100
MAX_POST_CHARS = 10_000
MAX_PHRASES = 200
MAX_PHRASE_CHARS = 200
RULES_VERSION = "thread-lint-rules/1"
COUNT_CONVENTION = "unicode-nfc-code-points;url=23"
THREAD_DRAFT_VERSION = "thread-draft/1"
NUMBERING_STYLES = ("n/N", "n/")

# What a program cannot decide. Reported on every lint so a clean result never reads as approval.
NEEDS_REVIEW = (
    "hook_quality",
    "one_idea",
    "stands_alone",
    "takeaway_quality",
    "source_supports_claims",
    "avoid_ai_writing_beyond_supplied_phrases",
)

_URL = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", re.IGNORECASE)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NUMBERING = {
    "n/N": re.compile(r"^([1-9][0-9]{0,2})/([1-9][0-9]{0,2})(?: |$)"),
    "n/": re.compile(r"^([1-9][0-9]{0,2})/(?: |$)"),
}
# A later line of a post that starts like a numbered post: a post hiding another post.
_HIDDEN_POST = re.compile(r"^[ \t]*[0-9]{1,3}/(?:[0-9]{1,3})?(?: |$)", re.MULTILINE)
_ZWJ = "\u200d"
_TAG_FIRST, _TAG_LAST, _BLACK_FLAG = 0xE0020, 0xE007F, "\U0001f3f4"
_REPEAT_THRESHOLD = 0.8
_MIN_WORDS_BESIDE_LINK = 3


class ThreadDraftError(ValueError):
    """The draft is not a well-formed thread-draft/1; the message is a fixed phrase."""


@dataclass(frozen=True)
class Finding:
    code: str
    post: int | None
    message: str
    next: str

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "post": self.post, "message": self.message, "next": self.next}


def count_post(text: str) -> int:
    """Length under the frozen convention: NFC code points, each URL counted as 23."""
    normalized = unicodedata.normalize("NFC", text)
    return len(_URL.sub("", normalized)) + URL_WEIGHT * len(_URL.findall(normalized))


def _words(text: str) -> list[str]:
    return [item.casefold() for item in _WORD.findall(text)]


def _body(text: str, style: str) -> str:
    return _NUMBERING[style].sub("", text, count=1)


def _validated(draft: Any) -> tuple[list[str], str, str, list[str]]:
    if not isinstance(draft, dict):
        raise ThreadDraftError("draft must be a JSON object")
    allowed = {"schema", "numbering", "posts", "source", "forbidden_phrases"}
    if set(draft) - allowed:
        raise ThreadDraftError("draft has an unknown field")
    if draft.get("schema") != THREAD_DRAFT_VERSION:
        raise ThreadDraftError("draft schema must be thread-draft/1")
    style = draft.get("numbering")
    if style not in NUMBERING_STYLES:
        raise ThreadDraftError("numbering must be n/N or n/")
    posts = draft.get("posts")
    if not isinstance(posts, list) or not 1 <= len(posts) <= MAX_POSTS:
        raise ThreadDraftError("posts must be a list of 1 to 100 strings")
    if not all(isinstance(item, str) and len(item) <= MAX_POST_CHARS for item in posts):
        raise ThreadDraftError("every post must be a string of at most 10000 characters")
    source = draft.get("source", "")
    if not isinstance(source, str) or len(source) > MAX_POST_CHARS:
        raise ThreadDraftError("source must be a string of at most 10000 characters")
    phrases = draft.get("forbidden_phrases", [])
    if (
        not isinstance(phrases, list)
        or len(phrases) > MAX_PHRASES
        or not all(isinstance(p, str) and 0 < len(p) <= MAX_PHRASE_CHARS for p in phrases)
    ):
        raise ThreadDraftError("forbidden_phrases must be a short list of non-empty strings")
    return posts, style, source, phrases


def _numbering_findings(posts: list[str], style: str) -> list[Finding]:
    found: list[Finding] = []
    pattern = _NUMBERING[style]
    totals: set[int] = set()
    for index, text in enumerate(posts, start=1):
        match = pattern.match(unicodedata.normalize("NFC", text))
        if match is None:
            found.append(
                Finding(
                    "T010",
                    index,
                    "post does not start with the declared numbering",
                    f"start post {index} with its number in the {style} form",
                )
            )
            continue
        if int(match.group(1)) != index:
            found.append(
                Finding(
                    "T011",
                    index,
                    f"post carries number {match.group(1)}, expected {index}",
                    "renumber the posts in order from 1",
                )
            )
        if style == "n/N":
            totals.add(int(match.group(2)))
    if style == "n/N" and totals and totals != {len(posts)}:
        found.append(
            Finding(
                "T012",
                None,
                "the total in the numbering does not equal the number of posts",
                f"use {len(posts)} as the total in every post",
            )
        )
    return found


def _is_emojiish(char: str) -> bool:
    return unicodedata.category(char) in {"So", "Sk"} or char == "\ufe0f"


def _hidden_characters(text: str) -> bool:
    """True if the post has a control, invisible or ambiguous-space character.

    Allowed: a newline, a plain space, a joiner between emoji (a sequence the platform draws
    as one picture) and the tag characters of a subdivision flag after a black flag.
    """
    for index, char in enumerate(text):
        if char in {" ", "\n"}:
            continue
        category = unicodedata.category(char)
        if char == _ZWJ:
            before = text[index - 1] if index else ""
            after = text[index + 1] if index + 1 < len(text) else ""
            if before and after and _is_emojiish(before) and unicodedata.category(after) == "So":
                continue
            return True
        if _TAG_FIRST <= ord(char) <= _TAG_LAST:
            run = index
            while run and _TAG_FIRST <= ord(text[run - 1]) <= _TAG_LAST:
                run -= 1
            if run and text[run - 1] == _BLACK_FLAG:
                continue
            return True
        if category in {"Cc", "Cf", "Zl", "Zp"} or char.isspace():
            return True
    return False


def _tokens(text: str) -> set[str]:
    return set(_words(text))


def lint_thread(draft: Any) -> dict[str, object]:
    """Lint one thread-draft/1; return the lint result. Raises ThreadDraftError if malformed."""
    posts, style, source, phrases = _validated(draft)
    findings: list[Finding] = []
    lengths = [count_post(item) for item in posts]
    for index, length in enumerate(lengths, start=1):
        if length > POST_LIMIT:
            findings.append(
                Finding(
                    "T001",
                    index,
                    f"post counts {length} against a limit of {POST_LIMIT}",
                    f"cut {length - POST_LIMIT} characters or split the post",
                )
            )
    findings.extend(_numbering_findings(posts, style))
    bodies = [_body(unicodedata.normalize("NFC", item), style) for item in posts]
    for index, text in enumerate(posts, start=1):
        normalized = unicodedata.normalize("NFC", text)
        if _hidden_characters(normalized):
            findings.append(
                Finding(
                    "T020",
                    index,
                    "post has a control, invisible or ambiguous-space character",
                    "remove it; use plain spaces and newlines only",
                )
            )
        if any(_HIDDEN_POST.match(line) for line in normalized.split("\n")[1:]):
            findings.append(
                Finding(
                    "T013",
                    index,
                    "a later line of the post starts like a numbered post",
                    "split it into its own post or remove the numbering from the line",
                )
            )
    for index, body in enumerate(bodies, start=1):
        if not _words(_URL.sub("", body)):
            findings.append(
                Finding(
                    "T002",
                    index,
                    "post has no text besides its number and links",
                    "write the post as a complete statement",
                )
            )
        elif _URL.search(body) and len(_words(_URL.sub("", body))) < _MIN_WORDS_BESIDE_LINK:
            findings.append(
                Finding(
                    "T031",
                    index,
                    "post is little more than a link, so it depends on the link",
                    "state the point in words; keep any link as extra",
                )
            )
    if not source.strip():
        findings.append(
            Finding(
                "T050",
                None,
                "no source is given outside the posts",
                "put the source in the draft's source field, not in a post",
            )
        )
    if len(posts) > 1:
        last = _tokens(bodies[-1])
        for index, body in enumerate(bodies[:-1], start=1):
            earlier = _tokens(body)
            union = last | earlier
            if union and len(last & earlier) / len(union) >= _REPEAT_THRESHOLD:
                findings.append(
                    Finding(
                        "T040",
                        len(posts),
                        f"the last post repeats post {index}",
                        "give the last post the takeaway instead of repeating a post",
                    )
                )
                break
    for index, text in enumerate(posts, start=1):
        folded = unicodedata.normalize("NFC", text).casefold()
        for phrase in phrases:
            if unicodedata.normalize("NFC", phrase).casefold() in folded:
                findings.append(
                    Finding(
                        "T900",
                        index,
                        "post contains a phrase the caller forbids",
                        "rewrite the post without the supplied phrase",
                    )
                )
                break
    findings.sort(key=lambda f: (f.post if f.post is not None else 0, f.code))
    return {
        "ok": not findings,
        "linter": {
            "name": "zeocreator.lint-thread",
            "version": __version__,
            "rules": RULES_VERSION,
        },
        "outcome": "clean" if not findings else "findings",
        "convention": COUNT_CONVENTION,
        "limit": POST_LIMIT,
        "post_count": len(posts),
        "lengths": lengths,
        "findings": [item.as_dict() for item in findings],
        "needs_review": list(NEEDS_REVIEW),
    }
