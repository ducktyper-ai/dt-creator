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
| `T010` | A post does not start with the declared numbering |
| `T011` | A post carries the wrong number |
| `T012` | The total in `n/N` is not the number of posts |
| `T031` | A post is little more than a link, so it depends on the link |
| `T040` | The last post repeats an earlier post |
| `T050` | No source outside the posts |
| `T900` | A post contains a phrase you supplied as forbidden |

## What it cannot check

A program cannot judge meaning. Every result lists `needs_review`: `hook_quality`,
`one_idea`, `stands_alone`, `takeaway_quality` and
`avoid_ai_writing_beyond_supplied_phrases`. A clean result means the structure passes, not
that the thread is good. A person or a runner-side reviewer decides the rest.

## Output and exit codes

One JSON line, schema `zeocreator.thread-lint/v1`, with `ok`, `outcome`, `convention`,
`limit`, `post_count`, `lengths`, `findings` and `needs_review`. Each finding names its
`code`, `post`, `message` and `next`.

| Exit | Meaning |
|---|---|
| 0 | Clean |
| 20 | One or more findings |
| 2 | The draft could not be read or is not `thread-draft/1`; the input is never echoed |
| 1 | Internal error |

The linter is a module (`zeo_creator.thread_lint.lint_thread`) and a command. It is not a
registered capability, so it does not change the runtime-provider inventory.
