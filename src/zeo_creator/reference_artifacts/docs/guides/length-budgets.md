# Check a draft against length budgets

`zeo-creator check-length-budgets` checks drafted text against word budgets you supply. It
is offline and pure. It calls no model, provider or network, ships no budgets of its own and
trims nothing: a section outside its budget is named, never cut.

```console
zeo-creator check-length-budgets --file budgets.json
zeo-creator check-length-budgets --file - < budgets.json
```

## The input: `length-budgets/1`

```json
{
  "budgets": {"intro": [40, 80], "item": [20, 60], "outro": [10, 40]},
  "sections": {"intro": "Opening text.", "item": ["First item.", "Second item."]},
  "subject": "A short subject",
  "subject_max_chars": 60,
  "preheader": "A short preheader",
  "preheader_max_chars": 100,
  "overall_max_words": 400
}
```

- `budgets` maps a section name to `[minimum words, maximum words]` for each item.
- `sections` maps a section name to one text or a list of texts, each checked on its own.
  A section with no budget is a breach. Its words still count toward the overall limit.
- `subject`, `preheader` and the three limits are optional; a limit you leave out is not
  checked. URLs are not counted as words.
- The budgets above are examples. Every number comes from the caller.

## The result

```json
{"breaches": ["intro 1: 2 words, expected 40 to 80"], "ok": false, "schema": "zeocreator.length-budgets/v1"}
```

Exit status `0` means every budget holds, `20` means at least one is broken, and `2` means
the input is not a `length-budgets/1` object (the error schema, with a fixed reason).
