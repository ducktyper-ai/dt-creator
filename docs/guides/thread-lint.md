# Lint a post thread

`zeo-creator lint-thread` checks the structure of a thread: a numbered series of short
posts with its source beside them. It is offline and pure. It calls no model, provider or
network, and it ships no house word list.

```console
zeo-creator lint-thread --file thread.json
zeo-creator lint-thread --file - < thread.json
```

## The draft: `thread-draft/1`

```json
{
  "schema": "thread-draft/1",
  "numbering": "n/N",
  "posts": ["1/2 First post, numbered as published.", "2/2 Second post."],
  "source": "Where the claims come from; it stays outside the posts.",
  "forbidden_phrases": []
}
```

- `numbering` is `n/N` (`1/4`) or `n/` (`1/`), at the start of every post.
- Each post is the text as published, numbering included, so its length is exact.
- `source` sits outside the posts. `forbidden_phrases` is optional: phrases your runner
  forbids (for example from an avoid-AI-writing list). None ship with Creator.

## What it checks

Length is counted as Unicode code points after NFC normalization, with each URL counted as
23. That is one frozen convention; it is not bytes, graphemes or any platform's weighting.

| Code | Finding |
|---|---|
| `T001` | A post counts more than 280 including its numbering |
| `T002` | A post has no text besides its number and links |
| `T010` | A post does not start with the declared numbering (ASCII digits, no leading zero, one ASCII space after) |
| `T011` | A post carries the wrong number |
| `T013` | A later line of a post starts like a numbered post, so a post hides inside another |
| `T012` | The total in `n/N` is not the number of posts |
| `T020` | A post has a control, invisible or ambiguous-space character (NUL, ESC, tab, no-break space, line or paragraph separator, zero-width, bidi, byte-order-mark or soft-hyphen characters). A newline and a plain space are allowed; so are an emoji joiner inside an emoji sequence and a subdivision flag's tag characters |
| `T031` | A post is little more than a link, so it depends on the link |
| `T040` | The last post repeats an earlier post |
| `T050` | No source outside the posts |
| `T900` | A post contains a phrase you supplied as forbidden |

## Definitions

- **URL:** `http://` or `https://` (any letter case) followed by ASCII URL characters. A
  scheme-less domain counts as ordinary text. Text glued to a URL without a space counts as
  text, not as part of the URL.
- **T031 (link-dependent):** a post with a link and fewer than 3 words beside it. A run of
  CJK characters counts as one word, so a CJK post with a link can trip it.
- **T040 (repeating last post):** the last post's words overlap an earlier post's by 80%
  (Jaccard) or more.
- **Size:** 1 to 100 posts, each at most 10000 characters, and a draft of at most 1 MB.
  One post is lintable, but a thread is usually more; check your own minimum.
- **Characters:** some platforms weight a character such as CJK as 2. This linter counts it
  as 1, so for such text leave a larger margin than for Latin text.

## What it cannot check

A program cannot judge meaning. Every result lists `needs_review`: `hook_quality`,
`one_idea`, `stands_alone`, `takeaway_quality` and
`source_supports_claims` (it checks that a source is given, not that it supports the claims) and `avoid_ai_writing_beyond_supplied_phrases`. A clean result means the structure passes, not
that the thread is good. A person or a runner-side reviewer decides the rest.

## Output and exit codes

One JSON line, schema `zeocreator.thread-lint/v1`, with `ok`, `outcome`, `convention`,
`limit`, `linter` (name, package version and `thread-lint-rules/1`), `post_count`, `lengths`, `findings` and `needs_review`. Each finding names its
`code`, `post`, `message` and `next`.

| Exit | Meaning |
|---|---|
| 0 | Clean |
| 20 | One or more findings |
| 2 | The draft could not be read, is larger than 1 MB, has a duplicate key, is not valid JSON or is not `thread-draft/1`; the input is never echoed |
| 1 | Internal error |

The linter is a module (`zeo_creator.thread_lint.lint_thread`) and a command. It is not a
registered capability, so it does not change the runtime-provider inventory.
