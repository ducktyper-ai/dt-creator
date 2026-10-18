---
name: thread-authoring
description: Write a numbered post thread (one idea, a hook in post 1, a takeaway in the last post, at most 280 characters per post) and check its structure with zeo-creator lint-thread.
---

# Write a thread

A thread is one idea told in numbered posts, each short enough to stand alone. This skill
is the format. `zeo-creator lint-thread` checks the structure; you check the meaning.

## The format

1. **One idea.** State it in one sentence before you write. If you need "and also", it is
   two threads.
2. **The hook is in post 1.** Post 1 says what the reader gets and why it matters, in its own
   words. It does not open with "Thread:", a greeting, or a promise to explain later.
3. **Each post stands alone.** A reader who sees only post 3 can follow it: name the thing,
   do not say "this" or "as above" for something in another post.
4. **At most 280 characters per post, numbering included.** Count the number. A URL counts
   as 23. The linter uses Unicode code points after NFC normalization; that is one fixed
   convention, not any platform's own weighting, so leave a margin of a few characters, and a wider one for CJK text, which some platforms count as 2 per character.
5. **Consistent numbering.** Start each post with `1/N`, `2/N` and so on, with the same `N`
   in every post, or `1/`, `2/` if you do not state a total.
6. **A worked example where one fits.** A concrete case with numbers beats a rule. Skip it
   when the idea has no case to show.
7. **The last post is the takeaway.** One sentence the reader can act on or repeat. No closing
   disclaimer, no repeat of an earlier post, no call to follow.
8. **The source sits outside the posts.** Keep it in the draft's `source` field, and cite it
   where you publish. No post depends on a link: say the point in words, and treat a link as
   extra.
9. **Plain writing, per post.** Apply your avoid-AI-writing rules to every post separately.
   Creator ships no word list; pass your own phrases as `forbidden_phrases` and the linter
   flags them.

## Check it

Write the draft as `thread-draft/1` JSON (see `docs/guides/thread-lint.md`) and run:

```console
zeo-creator lint-thread --file thread.json
```

Exit 0 is clean, 20 means findings (each names a post and what to change), 2 means the draft
could not be read. Fix the findings and run it again.

## What the linter cannot tell you

A clean result is not approval. Read the result's `needs_review` list and judge these
yourself or send the thread to a reviewer: whether the hook earns attention, whether it is
really one idea, whether each post stands alone, whether the last post is the takeaway, and
whether the source supports the claims, and whether the writing is plain beyond the phrases you supplied.

## A worked example

The example below is the passing fixture `tests/fixtures/threads/pass-basic.json`, a made-up
thread used only to show the format.

```text
1/4 A kitchen scale beats measuring cups for bread. Same flour, same water, a loaf that rises the same way every week.
2/4 A cup of flour can weigh 120 grams or 160 grams, depending on how it was scooped. That gap is a third of the dough.
3/4 Example: 500 g flour and 350 g water is a 70% hydration dough. Weigh both, and the next loaf matches this one.
4/4 Takeaway: weigh your ingredients once, write the numbers down, and your bread stops being a surprise.
```
